# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
Independent MCP tools for Knowledge Base operations.

This module provides MCP tool implementations that use the KnowledgeOrchestrator
service layer, supporting complete business workflows with Celery-based async
task scheduling.

These tools are registered with the MCP server and exposed to AI agents for
managing knowledge bases and documents.

Tools are declared using @mcp_tool decorator which provides:
- Automatic parameter schema extraction
- token_info auto-injection from MCP context
- Custom name/description support
- Parameter filtering (token_info is hidden from MCP schema)
"""

import asyncio
import logging
import threading
from typing import Any, Callable, Coroutine, Dict, Optional, TypeVar

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.mcp_server.auth import TaskTokenInfo
from app.mcp_server.knowledge_access import get_user_from_token
from app.mcp_server.tools.decorator import build_mcp_tools_dict, mcp_tool
from app.models.user import User
from app.services.knowledge.orchestrator import (
    MAX_DOCUMENT_READ_LIMIT,
    knowledge_orchestrator,
)
from app.services.rag.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)
T = TypeVar("T")


def _get_user_from_token(db: Session, token_info: TaskTokenInfo) -> Optional[User]:
    """Get user from token info."""
    return db.query(User).filter(User.id == token_info.user_id).first()


def _run_async_from_sync(
    async_func: Callable[..., Coroutine[Any, Any, T]],
    *args: Any,
    **kwargs: Any,
) -> T:
    """Run async work from a synchronous MCP tool without breaking active loops."""

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(async_func(*args, **kwargs))

    result_holder: Dict[str, T] = {}
    error_holder: Dict[str, BaseException] = {}

    def _runner() -> None:
        try:
            result_holder["value"] = asyncio.run(async_func(*args, **kwargs))
        except BaseException as exc:
            error_holder["value"] = exc

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()

    if "value" in error_holder:
        raise error_holder["value"]

    return result_holder["value"]


async def _retrieve_chunks_for_mcp(
    *,
    query: str,
    knowledge_base_id: int,
    top_k: int,
    document_ids: Optional[list[int]],
    user_id: int,
    user_name: str,
    user_subtask_id: int,
) -> Dict[str, Any]:
    """Run chunk retrieval with a session owned by the executing thread."""

    db = SessionLocal()
    try:
        retrieval_service = RetrievalService()
        return await retrieval_service.retrieve_for_chat_shell(
            query=query,
            knowledge_base_ids=[knowledge_base_id],
            db=db,
            max_results=top_k,
            document_ids=document_ids,
            user_name=user_name,
            route_mode="rag_retrieval",
            user_id=user_id,
            user_subtask_id=user_subtask_id,
            context_window=None,
            used_context_tokens=0,
            reserved_output_tokens=4096,
            context_buffer_ratio=0.1,
            max_direct_chunks=500,
            restricted_mode=False,
        )
    finally:
        db.close()


def _format_chunk_search_result(
    result: Dict[str, Any],
    knowledge_base_id: int,
) -> Dict[str, Any]:
    """Normalize retrieval output into the MCP chunk-search response shape."""

    items = []
    for record in result.get("records", []):
        metadata = record.get("metadata") or {}
        raw_document_id = metadata.get("doc_ref")
        document_id = int(raw_document_id) if raw_document_id is not None else None
        chunk_id = metadata.get("chunk_id", metadata.get("chunk_index"))
        items.append(
            {
                "document_id": document_id,
                "document_name": record.get("title", "Unknown"),
                "chunk_id": chunk_id,
                "content": record.get("content", ""),
                "score": record.get("score"),
                "kb_id": record.get("knowledge_base_id", knowledge_base_id),
            }
        )

    return {
        "mode": result.get("mode", "rag_retrieval"),
        "total": len(items),
        "items": items,
    }


def _search_knowledge_base_impl(
    token_info: TaskTokenInfo,
    *,
    knowledge_base_id: int,
    query: str,
    max_results: int,
    document_ids: Optional[list[int]] = None,
) -> Dict[str, Any]:
    """Shared implementation for MCP knowledge-base search tools."""

    db = SessionLocal()
    try:
        user = get_user_from_token(db, token_info)
        if not user:
            return {"error": "User not found", "total": 0, "items": []}
        user_id = user.id
        user_name = user.user_name

    finally:
        db.close()

    try:
        result = _run_async_from_sync(
            _retrieve_chunks_for_mcp,
            query=query,
            knowledge_base_id=knowledge_base_id,
            top_k=max_results,
            document_ids=document_ids,
            user_id=user_id,
            user_name=user_name,
            user_subtask_id=token_info.subtask_id,
        )
        return _format_chunk_search_result(result, knowledge_base_id)

    except ValueError as e:
        logger.warning(f"[MCP] knowledge base search validation error: {e}")
        return {"error": str(e), "total": 0, "items": []}

    except Exception as e:
        logger.error(f"[MCP] knowledge base search error: {e}", exc_info=True)
        return {"error": str(e), "total": 0, "items": []}


@mcp_tool(
    name="list_knowledge_bases",
    description="List all knowledge bases accessible to the current user.",
    server="knowledge",
    param_descriptions={
        "scope": "Resource scope - 'all', 'personal', or 'group'",
        "group_name": "Group name (required when scope='group')",
    },
)
def list_knowledge_bases(
    token_info: TaskTokenInfo,
    scope: str = "all",
    group_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    List all knowledge bases accessible to the current user.

    Args:
        token_info: Task token information containing user context
        scope: Resource scope - "all", "personal", or "group"
        group_name: Group name (required when scope="group")

    Returns:
        Dict with total count and list of knowledge bases
    """
    db = SessionLocal()
    try:
        user = get_user_from_token(db, token_info)
        if not user:
            return {"error": "User not found", "total": 0, "items": []}

        result = knowledge_orchestrator.list_knowledge_bases(
            db=db,
            user=user,
            scope=scope,
            group_name=group_name,
        )

        return {
            "total": result.total,
            "items": [item.model_dump() for item in result.items],
        }

    except Exception as e:
        logger.error(f"[MCP] list_knowledge_bases error: {e}", exc_info=True)
        return {"error": str(e), "total": 0, "items": []}

    finally:
        db.close()


@mcp_tool(
    name="list_documents",
    description="List all documents in a knowledge base.",
    server="knowledge",
    param_descriptions={
        "knowledge_base_id": "Knowledge base ID to list documents from",
    },
)
def list_documents(
    token_info: TaskTokenInfo,
    knowledge_base_id: int,
) -> Dict[str, Any]:
    """
    List all documents in a knowledge base.

    Args:
        token_info: Task token information containing user context
        knowledge_base_id: Knowledge base ID

    Returns:
        Dict with total count and list of documents
    """
    db = SessionLocal()
    try:
        user = get_user_from_token(db, token_info)
        if not user:
            return {"error": "User not found", "total": 0, "items": []}

        result = knowledge_orchestrator.list_documents(
            db=db,
            user=user,
            knowledge_base_id=knowledge_base_id,
        )

        return {
            "total": result.total,
            "items": [item.model_dump() for item in result.items],
        }

    except ValueError as e:
        logger.warning(f"[MCP] list_documents validation error: {e}")
        return {"error": str(e), "total": 0, "items": []}

    except Exception as e:
        logger.error(f"[MCP] list_documents error: {e}", exc_info=True)
        return {"error": str(e), "total": 0, "items": []}

    finally:
        db.close()


@mcp_tool(
    name="knowledge_base_search",
    description="Search a knowledge base for relevant information using the same high-level tool name used in chat mode.",
    server="knowledge",
    param_descriptions={
        "knowledge_base_id": "Knowledge base ID to search",
        "query": "Search query for semantic retrieval",
        "max_results": "Maximum number of chunk matches to return (default: 5)",
        "document_ids": "Optional document IDs to restrict the search scope",
    },
)
def knowledge_base_search(
    token_info: TaskTokenInfo,
    knowledge_base_id: int,
    query: str,
    max_results: int = 5,
    document_ids: Optional[list[int]] = None,
) -> Dict[str, Any]:
    """Search a knowledge base for relevant chunks using a chat-shell-aligned tool name."""

    return _search_knowledge_base_impl(
        token_info,
        knowledge_base_id=knowledge_base_id,
        query=query,
        max_results=max_results,
        document_ids=document_ids,
    )


@mcp_tool(
    name="create_knowledge_base",
    description="Create a new knowledge base with auto-configuration for retriever, embedding, and summary model.",
    server="knowledge",
    param_descriptions={
        "name": "Knowledge base name",
        "description": "Optional description for the knowledge base",
        "namespace": "Namespace ('default' for personal, group name for group)",
        "kb_type": "Type of knowledge base ('notebook' or 'classic')",
        "summary_enabled": "Whether to enable summary generation",
    },
)
def create_knowledge_base(
    token_info: TaskTokenInfo,
    name: str,
    description: Optional[str] = None,
    namespace: str = "default",
    kb_type: str = "notebook",
    summary_enabled: bool = True,
) -> Dict[str, Any]:
    """
    Create a new knowledge base with auto-configuration.

    Configuration is automatically selected:
    - retriever: Auto-selects user's first available retriever (priority: user > public)
    - embedding: Auto-selects user's first available embedding model
    - summary_model: Uses the model from current task (via token_info.task_id)

    If no retriever or embedding model is available, the knowledge base will be
    created without RAG configuration.

    Args:
        token_info: Task token information containing user context
        name: Knowledge base name
        description: Optional description
        namespace: Namespace ("default" for personal, group name for group)
        kb_type: Type ("notebook" or "classic")
        summary_enabled: Enable summary generation

    Returns:
        Dict with created knowledge base information
    """
    db = SessionLocal()
    try:
        user = get_user_from_token(db, token_info)
        if not user:
            return {"error": "User not found"}

        result = knowledge_orchestrator.create_knowledge_base(
            db=db,
            user=user,
            name=name,
            description=description,
            namespace=namespace,
            kb_type=kb_type,
            summary_enabled=summary_enabled,
            task_id=token_info.task_id,  # For resolving summary model
        )

        return result.model_dump()

    except ValueError as e:
        logger.warning(f"[MCP] create_knowledge_base validation error: {e}")
        return {"error": str(e)}

    except Exception as e:
        logger.error(f"[MCP] create_knowledge_base error: {e}", exc_info=True)
        return {"error": str(e)}

    finally:
        db.close()


@mcp_tool(
    name="create_document",
    description="Create a document in a knowledge base. Supports text content, base64-encoded files, or URL scraping.",
    server="knowledge",
    param_descriptions={
        "knowledge_base_id": "Target knowledge base ID",
        "name": "Document name",
        "source_type": "Source type: 'text', 'file', or 'web'",
        "content": "Text content (for source_type='text')",
        "file_base64": "Base64-encoded file content (for source_type='file')",
        "file_extension": "File extension like 'txt', 'md', 'pdf' (for source_type='file')",
        "url": "URL to scrape (for source_type='web')",
        "trigger_indexing": "Whether to trigger RAG indexing (default: True)",
        "trigger_summary": "Whether to trigger summary generation (default: True)",
    },
)
def create_document(
    token_info: TaskTokenInfo,
    knowledge_base_id: int,
    name: str,
    source_type: str,
    content: Optional[str] = None,
    file_base64: Optional[str] = None,
    file_extension: Optional[str] = None,
    url: Optional[str] = None,
    trigger_indexing: bool = True,
    trigger_summary: bool = True,
) -> Dict[str, Any]:
    """
    Create a document in a knowledge base.

    Supports three input methods:
    - source_type="text": Direct text content via `content` parameter
    - source_type="file": Base64-encoded file via `file_base64` and `file_extension`
    - source_type="web": URL content scraping via `url` parameter

    RAG indexing and summary generation are scheduled via Celery tasks
    and return immediately after document creation.

    Args:
        token_info: Task token information containing user context
        knowledge_base_id: Target knowledge base ID
        name: Document name
        source_type: Source type ("text", "file", or "web")
        content: Text content (for source_type="text")
        file_base64: Base64-encoded file content (for source_type="file")
        file_extension: File extension (for source_type="file", e.g., "txt", "md", "pdf")
        url: URL to scrape (for source_type="web")
        trigger_indexing: Whether to trigger RAG indexing (default: True)
        trigger_summary: Whether to trigger summary generation (default: True)

    Returns:
        Dict with created document information
    """
    db = SessionLocal()
    try:
        user = get_user_from_token(db, token_info)
        if not user:
            return {"error": "User not found"}

        # Orchestrator now handles Celery scheduling internally
        result = knowledge_orchestrator.create_document_with_content(
            db=db,
            user=user,
            knowledge_base_id=knowledge_base_id,
            name=name,
            source_type=source_type,
            content=content,
            file_base64=file_base64,
            file_extension=file_extension,
            url=url,
            trigger_indexing=trigger_indexing,
            trigger_summary=trigger_summary,
        )

        return result.model_dump()

    except ValueError as e:
        logger.warning(f"[MCP] create_document validation error: {e}")
        return {"error": str(e)}

    except Exception as e:
        logger.error(f"[MCP] create_document error: {e}", exc_info=True)
        return {"error": str(e)}

    finally:
        db.close()


@mcp_tool(
    name="read_document_content",
    description="Read document content with offset/limit pagination.",
    server="knowledge",
    param_descriptions={
        "document_id": "Document ID to read",
        "offset": "Character offset to start reading from",
        "limit": "Maximum number of characters to return",
    },
)
def read_document_content(
    token_info: TaskTokenInfo,
    document_id: int,
    offset: int = 0,
    limit: int = MAX_DOCUMENT_READ_LIMIT,
) -> Dict[str, Any]:
    """
    Read raw document content with offset/limit pagination.

    Args:
        token_info: Task token information containing user context
        document_id: Document ID
        offset: Character offset to start reading from
        limit: Maximum number of characters to return (defaults to backend limit)

    Returns:
        Dict with document content slice and pagination metadata
    """
    db = SessionLocal()
    try:
        user = _get_user_from_token(db, token_info)
        if not user:
            return {"error": "User not found"}

        result = knowledge_orchestrator.read_document_content(
            db=db,
            user=user,
            document_id=document_id,
            offset=offset,
            limit=limit,
        )

        return result.model_dump()

    except ValueError as e:
        logger.warning(f"[MCP] read_document_content validation error: {e}")
        return {"error": str(e)}

    except Exception as e:
        logger.error(f"[MCP] read_document_content error: {e}", exc_info=True)
        return {"error": str(e)}

    finally:
        db.close()


@mcp_tool(
    name="update_document_content",
    description="Update document content. Only supports TEXT type documents.",
    server="knowledge",
    param_descriptions={
        "document_id": "Document ID to update",
        "content": "New content for the document",
        "trigger_reindex": "Whether to trigger RAG re-indexing (default: True)",
    },
)
def update_document_content(
    token_info: TaskTokenInfo,
    document_id: int,
    content: str,
    trigger_reindex: bool = True,
) -> Dict[str, Any]:
    """
    Update document content.

    Only supports TEXT type documents. Re-indexing is scheduled via Celery
    if trigger_reindex=True.

    Args:
        token_info: Task token information containing user context
        document_id: Document ID
        content: New content
        trigger_reindex: Whether to trigger RAG re-indexing (default: True)

    Returns:
        Dict with update status
    """
    db = SessionLocal()
    try:
        user = get_user_from_token(db, token_info)
        if not user:
            return {"error": "User not found"}

        # Orchestrator now handles Celery scheduling internally
        result = knowledge_orchestrator.update_document_content(
            db=db,
            user=user,
            document_id=document_id,
            content=content,
            trigger_reindex=trigger_reindex,
        )

        return result

    except ValueError as e:
        logger.warning(f"[MCP] update_document_content validation error: {e}")
        return {"error": str(e)}

    except Exception as e:
        logger.error(f"[MCP] update_document_content error: {e}", exc_info=True)
        return {"error": str(e)}

    finally:
        db.close()


# Build tool registry from decorated functions
# This maintains backward compatibility with the manual dict approach
KNOWLEDGE_MCP_TOOLS = build_mcp_tools_dict(server="knowledge")
