---
sidebar_position: 1
---

# Local Executor Knowledge Base Support Redesign

## Overview

This spec restores knowledge base support for executor local mode without replaying PR #678 verbatim. The current main branch already contains the backend preprocessing flow that resolves `knowledge_base_ids` and writes the KB-enhanced `system_prompt` into `ExecutionRequest`. What is missing is the runtime path that exposes retrieval tools through the unified knowledge MCP server and injects that MCP server into local executor agents.

The redesign covers three areas:

1. Backend unified knowledge MCP server gains read-only retrieval tools.
2. Local executor agents inject the unified knowledge MCP server when KBs are present.
3. Frontend code-task input hides the knowledge base selector on both desktop and mobile.

## Goals

- Restore knowledge base retrieval capability for local executor mode.
- Keep the unified `/mcp/knowledge/sse` endpoint as the single MCP surface for knowledge features.
- Reuse current backend context preprocessing instead of adding a new KB resolution path.
- Make ClaudeCode and Agno behave consistently in local mode.
- Keep frontend behavior consistent across desktop and mobile code pages.

## Non-Goals

- Do not redesign chat shell knowledge base behavior.
- Do not add a new executor feature flag for KB support.
- Do not refactor the whole MCP injection pipeline.
- Do not change knowledge base permissions, schemas, or task binding logic.
- Do not change knowledge selector UX outside the code-task visibility rule.

## Current State

### Backend

- The backend already resolves KB selections through chat preprocessing and writes the final values into `ExecutionRequest.knowledge_base_ids` and `ExecutionRequest.system_prompt`.
- The unified knowledge MCP server exists at `/mcp/knowledge/sse`.
- Only knowledge management tools are currently registered on that MCP server.
- Retrieval tools such as `knowledge_base_search`, `kb_ls`, and `kb_head` are not currently exposed through MCP.

### Executor

- ClaudeCode local mode does not inject the unified knowledge MCP server when KBs are selected.
- Agno local mode also does not inject the unified knowledge MCP server when KBs are selected.
- ClaudeCode currently uses bot-level prompt data and does not explicitly prefer the backend-enhanced KB prompt for local mode.

### Frontend

- The input controls still expose the knowledge base context selector on code tasks.
- Desktop and mobile input controls do not enforce the same code-task hiding rule.

## Design

### 1. Backend: Add Retrieval Tools to Unified Knowledge MCP

Add a new module at `backend/app/mcp_server/tools/kb_retrieval.py` with three read-only MCP tools:

- `knowledge_base_search(token_info, query, kb_id, max_results=5)`
- `kb_ls(token_info, kb_id)`
- `kb_head(token_info, document_id, offset=0, limit=50000)`

These tools are exposed under `server="knowledge"` so they appear on the existing unified knowledge MCP server.

#### Retrieval Tool Behavior

`knowledge_base_search`
- Uses the existing retrieval service instead of introducing a new retrieval path.
- Returns a normalized structure containing `results`, `total`, and `query`.
- Caps returned results by `max_results`.
- Returns an `error` field instead of raising raw exceptions to the MCP caller.

`kb_ls`
- Lists documents for a knowledge base directly from `KnowledgeDocument`.
- Returns document metadata that is useful for exploration: id, name, file extension, size, short summary, and active state.
- Returns an empty list for an empty knowledge base.
- Returns an `error` field instead of propagating raw exceptions.

`kb_head`
- Reads extracted text through the existing context service attachment path.
- Supports `offset` and `limit` pagination with a hard maximum limit to avoid oversized payloads.
- Returns a stable structure with `content`, `offset`, `returned_length`, `total_length`, `has_more`, and document metadata.
- Returns a clear error when the target document does not exist.

#### Registration Changes

Update `backend/app/mcp_server/server.py` so knowledge MCP registration imports both:

- `app.mcp_server.tools.knowledge`
- `app.mcp_server.tools.kb_retrieval`

Update `backend/app/mcp_server/tools/__init__.py` to export the retrieval tool registry alongside the existing management tool registry.

The endpoint remains unchanged:

- Root metadata: `/mcp/knowledge`
- Streamable HTTP transport: `/mcp/knowledge/sse`

### 2. Shared Prompt: Match the Unified MCP Surface

Update `shared/prompts/knowledge_base.py` so KB prompts reflect the new runtime reality:

- If management tools are already present in the tool list, agents should use them directly.
- If management tools are not present, agents may still fall back to `load_skill("wegent-knowledge")`.
- Retrieval guidance continues to prefer `knowledge_base_search` for content questions and `kb_ls` / `kb_head` for exploration.

This keeps prompt behavior aligned with the unified knowledge MCP server and avoids unnecessary skill loading when the tools are already available.

### 3. Executor: Inject Knowledge MCP in Local Mode

The trigger rule is intentionally simple:

- If `ExecutionRequest.knowledge_base_ids` is non-empty
- And executor mode is `local`
- Then inject `wegent-knowledge` pointing to `<backend_url>/mcp/knowledge/sse`

No extra feature flag is introduced.

#### ClaudeCode

Update `executor/agents/claude_code/config_manager.py`:

- Merge a `wegent-knowledge` MCP server into the bot configuration when KBs are present in local mode.
- Use `Authorization: Bearer <auth_token>` headers from `ExecutionRequest`.
- Preserve any existing non-KB MCP server configuration.
- If backend has already written a KB-enhanced `task_data.system_prompt`, prefer that prompt over the raw bot prompt.

This keeps local ClaudeCode aligned with the same KB intent-routing rules already computed on the backend.

#### Agno

Update `executor/agents/agno/config_utils.py`:

- Merge the same `wegent-knowledge` MCP server into extracted `mcp_servers` when KBs are present in local mode.
- Preserve existing MCP servers.
- Prefer the backend-enhanced `task_data.system_prompt` in the extracted options when available.

No changes are needed in Agno MCP connection internals because `MCPManager.setup_mcp_tools()` already consumes the final `mcp_servers` configuration.

### 4. Frontend: Hide KB Context Selector on Code Tasks

Update:

- `frontend/src/features/tasks/components/input/ChatInputControls.tsx`
- `frontend/src/features/tasks/components/input/MobileChatInputControls.tsx`

Behavior:

- When `taskType === 'code'`, do not render the knowledge base context selector.
- The same rule must apply on desktop and mobile.
- All other task types keep the existing behavior.

This is a visibility-only change. It does not affect backend KB binding, permissions, or runtime execution.

## Data Flow

1. The user selects KBs in the existing chat/task flow.
2. Backend chat preprocessing resolves KB access and writes:
   - `ExecutionRequest.knowledge_base_ids`
   - `ExecutionRequest.system_prompt` with KB instructions
3. Local executor receives the request.
4. ClaudeCode or Agno detects KB presence and injects `wegent-knowledge`.
5. The agent connects to `/mcp/knowledge/sse`.
6. The agent uses retrieval tools through the unified MCP server under the KB-enhanced system prompt.

This design intentionally keeps KB resolution in one place: backend preprocessing. Executor only consumes the resolved request.

## Error Handling

### Backend MCP Tools

- Retrieval tool failures return structured error payloads.
- `kb_ls` returns an empty list for empty knowledge bases.
- `kb_head` clamps oversized `limit` values and returns empty content if `offset` exceeds content length.
- Missing documents return a specific not-found error.

### Executor Injection

- KB MCP injection is local-mode only.
- Existing MCP server configuration is merged, not replaced.
- If no KBs are present, executor behavior remains unchanged.

### Frontend

- Hiding the selector is purely presentational.
- Existing non-code tasks keep their current controls.

## File-Level Change Plan

### Backend

- Create `backend/app/mcp_server/tools/kb_retrieval.py`
- Modify `backend/app/mcp_server/server.py`
- Modify `backend/app/mcp_server/tools/__init__.py`
- Add tests in `backend/tests/mcp_server/test_kb_retrieval_tools.py`

### Executor

- Modify `executor/agents/claude_code/config_manager.py`
- Modify `executor/agents/agno/config_utils.py`
- Add tests in `executor/tests/agents/test_kb_mcp_injection.py`

### Frontend

- Modify `frontend/src/features/tasks/components/input/ChatInputControls.tsx`
- Modify `frontend/src/features/tasks/components/input/MobileChatInputControls.tsx`
- Add or update component tests for code-task KB selector visibility

### Shared

- Modify `shared/prompts/knowledge_base.py`

## Testing Strategy

### Backend Tests

- Verify `knowledge_base_search` returns normalized results.
- Verify `knowledge_base_search` respects `max_results`.
- Verify retrieval failures return structured errors.
- Verify `kb_ls` returns document metadata.
- Verify `kb_ls` returns an empty list for empty KBs.
- Verify `kb_head` returns content and pagination metadata.
- Verify `kb_head` handles missing documents.
- Keep existing MCP route tests passing for `/mcp/knowledge` and `/mcp/knowledge/sse`.

### Executor Tests

- ClaudeCode injects `wegent-knowledge` when KBs are present in local mode.
- ClaudeCode does not inject KB MCP when no KBs are present.
- ClaudeCode prefers backend-enhanced `system_prompt`.
- Agno injects `wegent-knowledge` when KBs are present in local mode.
- Agno does not inject KB MCP when no KBs are present.
- Existing non-KB MCP configuration remains preserved after injection.

### Frontend Tests

- Desktop input hides KB selector for `taskType === 'code'`.
- Mobile input hides KB selector for `taskType === 'code'`.
- Non-code task types still show the selector when they did before.

## Risks and Mitigations

### Risk: Executor prompt and tool surface drift apart

Mitigation:
- Update `shared/prompts/knowledge_base.py` in the same change set as MCP tool registration.

### Risk: Agno and ClaudeCode diverge in local-mode behavior

Mitigation:
- Use the same injection trigger and the same MCP server name in both agents.

### Risk: Frontend hides KB selector but users still expect KB execution on code tasks

Mitigation:
- This spec treats the change as UI cleanup only. Existing task-bound KBs still work because runtime behavior is controlled by backend request data, not by frontend visibility.

## Acceptance Criteria

- A local executor task with KBs selected can use `knowledge_base_search`, `kb_ls`, and `kb_head` through `/mcp/knowledge/sse`.
- ClaudeCode and Agno both receive the injected `wegent-knowledge` MCP server in local mode when KBs are present.
- The KB-enhanced system prompt from backend is used by local executor agents.
- Code-task input no longer shows the KB context selector on desktop or mobile.
- New backend and executor tests pass for the restored behavior.
