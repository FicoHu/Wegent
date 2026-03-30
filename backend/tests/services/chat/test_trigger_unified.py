# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.models import ExecutionRequest
from shared.models.knowledge import ChatContextsResult, KnowledgeBaseToolsResult


@pytest.mark.unit
class TestBuildExecutionRequestUserSubtaskId:
    async def test_propagates_user_subtask_id_to_execution_request(self):
        """Ensure user_subtask_id is always propagated for downstream RAG persistence."""
        from app.services.chat.trigger import unified as trigger_unified

        mock_db = MagicMock()

        request_from_builder = ExecutionRequest(task_id=1, subtask_id=2)
        mock_builder = MagicMock()
        mock_builder.build.return_value = request_from_builder

        async def _process_contexts_passthrough(
            db,
            request,
            user_subtask_id,
            user_id,
        ):
            return request

        with patch.object(trigger_unified, "SessionLocal", return_value=mock_db):
            with patch(
                "app.services.execution.TaskRequestBuilder", return_value=mock_builder
            ):
                with patch.object(
                    trigger_unified,
                    "_process_contexts",
                    new=AsyncMock(side_effect=_process_contexts_passthrough),
                ) as mock_process_contexts:
                    task = MagicMock()
                    task.id = 1
                    task.json = {}

                    assistant_subtask = MagicMock()
                    assistant_subtask.id = 2

                    team = MagicMock()
                    user = MagicMock()
                    user.id = 7

                    result = await trigger_unified.build_execution_request(
                        task=task,
                        assistant_subtask=assistant_subtask,
                        team=team,
                        user=user,
                        message="hello",
                        payload=None,
                        user_subtask_id=123,
                    )

                    assert result.user_subtask_id == 123
                    mock_builder.build.assert_called_once()
                    mock_process_contexts.assert_awaited_once()

    async def test_device_execution_keeps_sandbox_path_in_context_processing(self):
        """Device-routed tasks should keep sandbox path placeholders for executor rewrite."""
        from app.services.chat.trigger import unified as trigger_unified

        mock_db = MagicMock()

        request_from_builder = ExecutionRequest(task_id=1, subtask_id=2)
        mock_builder = MagicMock()
        mock_builder.build.return_value = request_from_builder

        with patch.object(trigger_unified, "SessionLocal", return_value=mock_db):
            with patch(
                "app.services.execution.TaskRequestBuilder", return_value=mock_builder
            ):
                with patch.object(
                    trigger_unified,
                    "_process_contexts",
                    new=AsyncMock(return_value=request_from_builder),
                ) as mock_process_contexts:
                    task = MagicMock()
                    task.id = 1
                    task.json = {}

                    assistant_subtask = MagicMock()
                    assistant_subtask.id = 2

                    team = MagicMock()
                    user = MagicMock()
                    user.id = 7

                    await trigger_unified.build_execution_request(
                        task=task,
                        assistant_subtask=assistant_subtask,
                        team=team,
                        user=user,
                        message="hello",
                        payload=None,
                        user_subtask_id=123,
                        device_id="device-1",
                    )

                    mock_process_contexts.assert_awaited_once_with(
                        mock_db,
                        request_from_builder,
                        123,
                        7,
                    )

    async def test_does_not_process_contexts_when_user_subtask_id_is_none(self):
        """When user_subtask_id is missing, contexts processing should be skipped."""
        from app.services.chat.trigger import unified as trigger_unified

        mock_db = MagicMock()

        request_from_builder = ExecutionRequest(task_id=1, subtask_id=2)
        mock_builder = MagicMock()
        mock_builder.build.return_value = request_from_builder

        with patch.object(trigger_unified, "SessionLocal", return_value=mock_db):
            with patch(
                "app.services.execution.TaskRequestBuilder", return_value=mock_builder
            ):
                with patch.object(
                    trigger_unified, "_process_contexts", new=AsyncMock()
                ) as mock_process_contexts:
                    task = MagicMock()
                    task.id = 1
                    task.json = {}

                    assistant_subtask = MagicMock()
                    assistant_subtask.id = 2

                    team = MagicMock()
                    user = MagicMock()
                    user.id = 7

                    result = await trigger_unified.build_execution_request(
                        task=task,
                        assistant_subtask=assistant_subtask,
                        team=team,
                        user=user,
                        message="hello",
                        payload=None,
                        user_subtask_id=None,
                    )

                    assert result.user_subtask_id is None
                    mock_builder.build.assert_called_once()
                    mock_process_contexts.assert_not_awaited()


@pytest.mark.unit
class TestProcessContextsAttachments:
    @pytest.mark.asyncio
    async def test_populates_request_attachments_from_subtask_contexts(self):
        """Executor request should carry attachment metadata for local downloads."""
        from app.services.chat.trigger import unified as trigger_unified

        request = ExecutionRequest(
            task_id=1233,
            subtask_id=1643,
            prompt="hello",
            system_prompt="system",
            model_config={},
        )

        attachment_context = MagicMock()
        attachment_context.id = 274
        attachment_context.original_filename = "xxx.md"
        attachment_context.mime_type = "text/markdown"
        attachment_context.file_size = 57036
        attachment_context.subtask_id = 1642

        ctx = ChatContextsResult(
            final_message="processed",
            has_table_context=False,
            table_contexts=[],
            kb=KnowledgeBaseToolsResult(
                extra_tools=[],
                enhanced_system_prompt="enhanced",
                kb_meta_prompt="",
            ),
        )

        with patch(
            "app.services.chat.preprocessing.prepare_contexts_for_chat",
            new=AsyncMock(return_value=ctx),
        ):
            with patch(
                "app.services.chat.trigger.unified.context_service.get_attachments_by_subtask",
                return_value=[attachment_context],
            ):
                result = await trigger_unified._process_contexts(
                    db=MagicMock(),
                    request=request,
                    user_subtask_id=1642,
                    user_id=2,
                )

        assert result.prompt == "processed"
        assert result.system_prompt == "enhanced"
        assert result.attachments == [
            {
                "id": 274,
                "original_filename": "xxx.md",
                "mime_type": "text/markdown",
                "file_size": 57036,
                "subtask_id": 1642,
            }
        ]
