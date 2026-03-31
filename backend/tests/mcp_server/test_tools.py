# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for MCP Server tools."""

import importlib
import json
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.mcp_server.auth import TaskTokenInfo


def get_silent_exit_module():
    """Get the silent_exit module, handling import caching issues."""
    module_name = "app.mcp_server.tools.silent_exit"
    # Force import the module directly
    if module_name not in sys.modules:
        importlib.import_module(module_name)
    return sys.modules[module_name]


class TestSilentExitTool:
    """Tests for silent_exit tool."""

    def test_silent_exit_returns_marker(self):
        """Test that silent_exit returns the correct marker without token_info."""
        module = get_silent_exit_module()
        # When token_info is None, no database access is needed
        result = module.silent_exit(reason="test reason")
        parsed = json.loads(result)

        assert parsed["__silent_exit__"] is True
        assert parsed["reason"] == "test reason"

    def test_silent_exit_empty_reason(self):
        """Test silent_exit with empty reason."""
        module = get_silent_exit_module()
        # When token_info is None, no database access is needed
        result = module.silent_exit()
        parsed = json.loads(result)

        assert parsed["__silent_exit__"] is True
        assert parsed["reason"] == ""

    def test_silent_exit_with_token_info(self):
        """Test silent_exit with token info - verifies marker is returned."""
        module = get_silent_exit_module()

        token_info = TaskTokenInfo(
            task_id=123,
            subtask_id=456,
            user_id=789,
            user_name="testuser",
        )

        # Use object patching instead of string-based patching
        original_func = module._update_subtask_silent_exit
        mock_update = MagicMock()
        module._update_subtask_silent_exit = mock_update

        try:
            result = module.silent_exit(reason="completed", token_info=token_info)

            # Should attempt to update the database
            mock_update.assert_called_once_with(456, "completed")

            parsed = json.loads(result)
            assert parsed["__silent_exit__"] is True
            assert parsed["reason"] == "completed"
        finally:
            # Restore original function
            module._update_subtask_silent_exit = original_func


class TestSilentExitMarkerDetection:
    """Tests for detecting silent_exit marker in responses."""

    def test_detect_silent_exit_marker(self):
        """Test detection of __silent_exit__ marker in tool output."""
        tool_output = json.dumps({"__silent_exit__": True, "reason": "normal status"})

        parsed = json.loads(tool_output)
        assert parsed.get("__silent_exit__") is True
        assert parsed.get("reason") == "normal status"

    def test_non_silent_exit_output(self):
        """Test that normal output doesn't trigger false positive."""
        tool_output = json.dumps({"success": True, "data": "some data"})

        parsed = json.loads(tool_output)
        assert parsed.get("__silent_exit__") is not True

    def test_invalid_json_output(self):
        """Test handling of non-JSON output."""
        tool_output = "plain text output"

        try:
            parsed = json.loads(tool_output)
            is_silent = parsed.get("__silent_exit__")
        except json.JSONDecodeError:
            is_silent = False

        assert is_silent is False


class TestKnowledgeTools:
    """Tests for knowledge MCP tools."""

    def test_list_documents_uses_shared_user_lookup(self):
        """list_documents should use the shared token-to-user helper."""
        from app.mcp_server.tools import knowledge as knowledge_tools

        token_info = TaskTokenInfo(
            task_id=1,
            subtask_id=2,
            user_id=3,
            user_name="testuser",
        )
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_document = MagicMock()
        mock_document.model_dump.return_value = {"id": 52, "name": "AI Analysis"}
        mock_result = MagicMock(total=1, items=[mock_document])

        with (
            patch.object(knowledge_tools, "SessionLocal", return_value=mock_db),
            patch.object(
                knowledge_tools, "get_user_from_token", return_value=mock_user
            ),
            patch.object(
                knowledge_tools.knowledge_orchestrator,
                "list_documents",
                return_value=mock_result,
            ),
        ):
            result = knowledge_tools.list_documents(token_info, knowledge_base_id=1493)

        assert result == {
            "total": 1,
            "items": [{"id": 52, "name": "AI Analysis"}],
        }

    def test_read_document_content_returns_content_with_pagination_metadata(self):
        """read_document_content should return content via structured parameters."""
        from app.mcp_server.tools import knowledge as knowledge_tools

        token_info = TaskTokenInfo(
            task_id=1,
            subtask_id=2,
            user_id=3,
            user_name="testuser",
        )
        mock_session = MagicMock()
        mock_user = MagicMock()
        mock_result = MagicMock()
        expected_payload = {
            "document_id": 52,
            "name": "AI Analysis",
            "content": "DeepSeek and Doubao were the main players.",
            "total_length": 44,
            "offset": 0,
            "returned_length": 44,
            "has_more": False,
            "kb_id": 1493,
        }
        mock_result.model_dump.return_value = expected_payload

        with (
            patch.object(knowledge_tools, "SessionLocal", return_value=mock_session),
            patch.object(
                knowledge_tools, "get_user_from_token", return_value=mock_user
            ),
            patch.object(
                knowledge_tools.knowledge_orchestrator,
                "read_document_content",
                return_value=mock_result,
            ),
        ):
            result = knowledge_tools.read_document_content(
                token_info=token_info,
                document_id=52,
                offset=0,
                limit=44,
            )

        assert result == expected_payload

    def test_knowledge_base_search_alias_returns_chunk_matches(self):
        """knowledge_base_search should expose the same MCP search behavior."""
        from app.mcp_server.tools import knowledge as knowledge_tools

        token_info = TaskTokenInfo(
            task_id=1,
            subtask_id=2,
            user_id=3,
            user_name="testuser",
        )
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 3
        mock_user.user_name = "testuser"

        with (
            patch.object(knowledge_tools, "SessionLocal", return_value=mock_db),
            patch.object(
                knowledge_tools, "get_user_from_token", return_value=mock_user
            ),
            patch.object(
                knowledge_tools.RetrievalService,
                "retrieve_for_chat_shell",
                new=AsyncMock(
                    return_value={
                        "mode": "rag_retrieval",
                        "records": [
                            {
                                "content": "Holiday AI competition analysis.",
                                "score": 0.93,
                                "title": "AI Holiday Review",
                                "metadata": {
                                    "doc_ref": "52",
                                    "chunk_id": 3,
                                },
                                "knowledge_base_id": 1493,
                            }
                        ],
                        "total": 1,
                    }
                ),
            ),
        ):
            result = knowledge_tools.knowledge_base_search(
                token_info,
                knowledge_base_id=1493,
                query="AI competition",
                max_results=4,
                document_ids=[52],
            )

        assert result == {
            "mode": "rag_retrieval",
            "total": 1,
            "items": [
                {
                    "document_id": 52,
                    "document_name": "AI Holiday Review",
                    "chunk_id": 3,
                    "content": "Holiday AI competition analysis.",
                    "score": 0.93,
                    "kb_id": 1493,
                }
            ],
        }

    @pytest.mark.asyncio
    async def test_knowledge_base_search_works_inside_running_event_loop(self):
        """knowledge_base_search should work even when an event loop is already running."""
        from app.mcp_server.tools import knowledge as knowledge_tools

        token_info = TaskTokenInfo(
            task_id=1,
            subtask_id=2,
            user_id=3,
            user_name="testuser",
        )
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 3
        mock_user.user_name = "testuser"

        with (
            patch.object(knowledge_tools, "SessionLocal", return_value=mock_db),
            patch.object(
                knowledge_tools, "get_user_from_token", return_value=mock_user
            ),
            patch.object(
                knowledge_tools.RetrievalService,
                "retrieve_for_chat_shell",
                new=AsyncMock(
                    return_value={
                        "mode": "rag_retrieval",
                        "records": [
                            {
                                "content": "Chunk content from KB.",
                                "score": 0.88,
                                "title": "AI Competition",
                                "metadata": {
                                    "doc_ref": "52",
                                    "chunk_id": 9,
                                },
                                "knowledge_base_id": 1493,
                            }
                        ],
                        "total": 1,
                    }
                ),
            ),
        ):
            result = knowledge_tools.knowledge_base_search(
                token_info,
                knowledge_base_id=1493,
                query="AI competition",
                max_results=3,
            )

        assert result == {
            "mode": "rag_retrieval",
            "total": 1,
            "items": [
                {
                    "document_id": 52,
                    "document_name": "AI Competition",
                    "chunk_id": 9,
                    "content": "Chunk content from KB.",
                    "score": 0.88,
                    "kb_id": 1493,
                }
            ],
        }
