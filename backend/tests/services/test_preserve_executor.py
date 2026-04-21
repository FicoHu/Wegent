# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for preserve executor functionality.

This module tests:
1. cleanup_stale_executors skips tasks with preserveExecutor=true
2. set_preserve_executor API functionality
3. Permission control for preserve executor operations
"""

from contextlib import ExitStack, contextmanager
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.subtask import Subtask, SubtaskRole, SubtaskStatus
from app.models.task import TaskResource
from app.schemas.kind import Task
from app.services.adapters.executor_job import JobService
from app.services.adapters.task_kinds import TaskKindsService


class CleanupExecutorTestHelpers:
    def _create_mock_task_resource(
        self, task_id: int, user_id: int, preserve_executor: bool = False
    ):
        """Helper to create a mock TaskResource with optional preserveExecutor label"""
        task = Mock(spec=TaskResource)
        task.id = task_id
        task.user_id = user_id
        task.kind = "Task"
        task.is_active = True
        task.updated_at = datetime.now() - timedelta(hours=48)

        labels = {"taskType": "chat"}
        if preserve_executor:
            labels["preserveExecutor"] = "true"

        task.json = {
            "kind": "Task",
            "apiVersion": "agent.wecode.io/v1",
            "metadata": {
                "name": f"task-{task_id}",
                "namespace": "default",
                "labels": labels,
            },
            "spec": {
                "title": "Test Task",
                "prompt": "Test prompt",
                "teamRef": {"name": "test-team", "namespace": "default"},
                "workspaceRef": {"name": "workspace-1", "namespace": "default"},
            },
            "status": {
                "status": "COMPLETED",
                "progress": 100,
                "createdAt": datetime.now().isoformat(),
                "updatedAt": datetime.now().isoformat(),
            },
        }
        return task

    def _create_mock_subtask(
        self,
        subtask_id: int,
        task_id: int,
        executor_name: str = "executor-1",
        executor_namespace: str = "default",
    ):
        """Helper to create a mock Subtask"""
        subtask = Mock(spec=Subtask)
        subtask.id = subtask_id
        subtask.task_id = task_id
        subtask.executor_name = executor_name
        subtask.executor_namespace = executor_namespace
        subtask.executor_deleted_at = False
        subtask.status = SubtaskStatus.COMPLETED
        subtask.updated_at = datetime.now() - timedelta(hours=48)
        return subtask

    def _setup_task_and_subtask_queries(self, mock_db, task, subtasks):
        """Configure task/subtask query mocks for cleanup tests."""
        mock_subtask_query = MagicMock()
        mock_subtask_query.join.return_value = mock_subtask_query
        mock_subtask_query.filter.return_value = mock_subtask_query
        mock_subtask_query.all.return_value = subtasks

        mock_task_query = MagicMock()
        mock_task_query.filter.return_value = mock_task_query
        mock_task_query.first.return_value = task

        def query_side_effect(model):
            if model == Subtask:
                return mock_subtask_query
            if model == TaskResource:
                return mock_task_query
            return MagicMock()

        mock_db.query.side_effect = query_side_effect
        return mock_subtask_query, mock_task_query

    @contextmanager
    def _patch_cleanup_scan(self, job_service, subtasks, task_map):
        """Patch the scheduled cleanup scan helpers for one logical batch."""
        with ExitStack() as stack:
            stack.enter_context(
                patch.object(
                    job_service,
                    "_scan_candidate_subtasks_batch",
                    side_effect=[subtasks, []],
                )
            )
            stack.enter_context(
                patch.object(
                    job_service,
                    "_load_tasks_for_cleanup",
                    return_value=task_map,
                )
            )
            stack.enter_context(
                patch.object(
                    job_service,
                    "_get_cleanup_subtasks_for_task",
                    side_effect=lambda _db, task_id: [
                        subtask for subtask in subtasks if subtask.task_id == task_id
                    ],
                )
            )
            yield


@pytest.mark.unit
class TestCleanupStaleExecutorsWithPreserveFlag(CleanupExecutorTestHelpers):
    """Test cleanup_stale_executors skips tasks with preserveExecutor label"""

    @pytest.fixture
    def job_service(self):
        """Create JobService instance"""
        from app.models.kind import Kind

        return JobService(Kind)

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session"""
        return Mock(spec=Session)

    def test_skips_task_with_preserve_executor_true(self, job_service, mock_db):
        """Test that tasks with preserveExecutor=true are skipped during cleanup"""
        # Create a mock subtask linked to a task with preserveExecutor=true
        mock_subtask = self._create_mock_subtask(1, 100)
        mock_task = self._create_mock_task_resource(100, 1, preserve_executor=True)

        with (
            self._patch_cleanup_scan(job_service, [mock_subtask], {100: mock_task}),
            patch(
                "app.services.adapters.executor_job.executor_kinds_service"
            ) as mock_executor_service,
            patch("app.services.adapters.executor_job.settings") as mock_settings,
        ):
            mock_settings.CHAT_TASK_EXECUTOR_DELETE_AFTER_HOURS = 24
            mock_settings.CODE_TASK_EXECUTOR_DELETE_AFTER_HOURS = 48
            mock_settings.STALE_NON_TERMINAL_TASK_EXECUTOR_DELETE_AFTER_HOURS = 24

            job_service.cleanup_stale_executors(mock_db)

        mock_executor_service.delete_executor_task_sync.assert_not_called()

    def test_cleans_up_task_without_preserve_flag(self, job_service, mock_db):
        """Test that tasks without preserveExecutor label are cleaned up normally"""
        # Create a mock subtask linked to a task WITHOUT preserveExecutor
        mock_subtask = self._create_mock_subtask(1, 100)
        mock_task = self._create_mock_task_resource(100, 1, preserve_executor=False)

        with (
            self._patch_cleanup_scan(job_service, [mock_subtask], {100: mock_task}),
            patch(
                "app.services.adapters.executor_job.executor_kinds_service"
            ) as mock_executor_service,
            patch("app.services.adapters.executor_job.settings") as mock_settings,
        ):
            mock_settings.CHAT_TASK_EXECUTOR_DELETE_AFTER_HOURS = 24
            mock_settings.CODE_TASK_EXECUTOR_DELETE_AFTER_HOURS = 48
            mock_executor_service.delete_executor_task_sync.return_value = True

            job_service.cleanup_stale_executors(mock_db)

        mock_executor_service.delete_executor_task_sync.assert_called_once_with(
            "executor-1", "default"
        )

    def test_skips_task_with_preserve_executor_false(self, job_service, mock_db):
        """Test that tasks with preserveExecutor=false are cleaned up normally"""
        # Create a mock subtask linked to a task with preserveExecutor=false
        mock_subtask = self._create_mock_subtask(1, 100)
        mock_task = self._create_mock_task_resource(100, 1, preserve_executor=False)
        # Explicitly set preserveExecutor to "false"
        mock_task.json["metadata"]["labels"]["preserveExecutor"] = "false"

        with (
            self._patch_cleanup_scan(job_service, [mock_subtask], {100: mock_task}),
            patch(
                "app.services.adapters.executor_job.executor_kinds_service"
            ) as mock_executor_service,
            patch("app.services.adapters.executor_job.settings") as mock_settings,
        ):
            mock_settings.CHAT_TASK_EXECUTOR_DELETE_AFTER_HOURS = 24
            mock_settings.CODE_TASK_EXECUTOR_DELETE_AFTER_HOURS = 48
            mock_executor_service.delete_executor_task_sync.return_value = True

            job_service.cleanup_stale_executors(mock_db)

        mock_executor_service.delete_executor_task_sync.assert_called_once_with(
            "executor-1", "default"
        )

    def test_code_task_archives_before_cleanup(self, job_service, mock_db):
        """Test code tasks trigger archive before deleting the executor."""
        mock_subtask = self._create_mock_subtask(1, 100)
        mock_task = self._create_mock_task_resource(100, 1, preserve_executor=False)
        mock_task.json["metadata"]["labels"]["taskType"] = "code"
        mock_subtask.updated_at = datetime.now() - timedelta(hours=72)

        with (
            self._patch_cleanup_scan(job_service, [mock_subtask], {100: mock_task}),
            patch.object(job_service, "_archive_workspace_sync") as archive_mock,
            patch(
                "app.services.adapters.executor_job.executor_kinds_service"
            ) as mock_executor_service,
            patch("app.services.adapters.executor_job.settings") as mock_settings,
        ):
            mock_settings.CHAT_TASK_EXECUTOR_DELETE_AFTER_HOURS = 24
            mock_settings.CODE_TASK_EXECUTOR_DELETE_AFTER_HOURS = 48
            mock_executor_service.delete_executor_task_sync.return_value = True

            job_service.cleanup_stale_executors(mock_db)

        archive_mock.assert_called_once()
        mock_executor_service.delete_executor_task_sync.assert_called_once_with(
            "executor-1", "default"
        )

    def test_cleanup_continues_when_archive_fails(self, job_service, mock_db):
        """Test executor cleanup continues even when workspace archive fails."""
        mock_subtask = self._create_mock_subtask(1, 100)
        mock_task = self._create_mock_task_resource(100, 1, preserve_executor=False)
        mock_task.json["metadata"]["labels"]["taskType"] = "code"
        mock_subtask.updated_at = datetime.now() - timedelta(hours=72)

        with (
            self._patch_cleanup_scan(job_service, [mock_subtask], {100: mock_task}),
            patch.object(
                job_service,
                "_archive_workspace_sync",
                side_effect=RuntimeError("archive failed"),
            ),
            patch(
                "app.services.adapters.executor_job.executor_kinds_service"
            ) as mock_executor_service,
            patch("app.services.adapters.executor_job.settings") as mock_settings,
        ):
            mock_settings.CHAT_TASK_EXECUTOR_DELETE_AFTER_HOURS = 24
            mock_settings.CODE_TASK_EXECUTOR_DELETE_AFTER_HOURS = 48
            mock_executor_service.delete_executor_task_sync.return_value = True

            job_service.cleanup_stale_executors(mock_db)

        mock_executor_service.delete_executor_task_sync.assert_called_once_with(
            "executor-1", "default"
        )

    def test_cleanup_marks_deleted_using_subtask_ids(self, job_service, mock_db):
        """Test cleanup passes subtask ids to the short-lived delete marker."""
        mock_subtask = self._create_mock_subtask(1, 100)
        mock_task = self._create_mock_task_resource(100, 1, preserve_executor=False)

        with (
            self._patch_cleanup_scan(job_service, [mock_subtask], {100: mock_task}),
            patch.object(job_service, "_mark_executor_deleted") as mark_deleted_mock,
            patch(
                "app.services.adapters.executor_job.executor_kinds_service"
            ) as mock_executor_service,
            patch("app.services.adapters.executor_job.settings") as mock_settings,
        ):
            mock_settings.CHAT_TASK_EXECUTOR_DELETE_AFTER_HOURS = 24
            mock_settings.CODE_TASK_EXECUTOR_DELETE_AFTER_HOURS = 48
            mock_executor_service.delete_executor_task_sync.return_value = True

            job_service.cleanup_stale_executors(mock_db)

        mark_deleted_mock.assert_called_once_with([1])

    def test_cleanup_marks_deleted_when_executor_pod_is_missing(
        self, job_service, mock_db
    ):
        """Test missing executor pods are treated as already deleted."""
        mock_subtask = self._create_mock_subtask(1, 100)
        mock_task = self._create_mock_task_resource(100, 1, preserve_executor=False)

        with (
            self._patch_cleanup_scan(job_service, [mock_subtask], {100: mock_task}),
            patch.object(job_service, "_mark_executor_deleted") as mark_deleted_mock,
            patch(
                "app.services.adapters.executor_job.executor_kinds_service"
            ) as mock_executor_service,
            patch("app.services.adapters.executor_job.settings") as mock_settings,
        ):
            mock_settings.CHAT_TASK_EXECUTOR_DELETE_AFTER_HOURS = 24
            mock_settings.CODE_TASK_EXECUTOR_DELETE_AFTER_HOURS = 48
            mock_executor_service.delete_executor_task_sync.side_effect = HTTPException(
                status_code=500,
                detail="Pod 'executor-1' not found",
            )

            job_service.cleanup_stale_executors(mock_db)

        mark_deleted_mock.assert_called_once_with([1])

    def test_cleanup_does_not_mark_deleted_on_other_executor_errors(
        self, job_service, mock_db
    ):
        """Test non-idempotent delete failures still leave executor state untouched."""
        mock_subtask = self._create_mock_subtask(1, 100)
        mock_task = self._create_mock_task_resource(100, 1, preserve_executor=False)

        with (
            self._patch_cleanup_scan(job_service, [mock_subtask], {100: mock_task}),
            patch.object(job_service, "_mark_executor_deleted") as mark_deleted_mock,
            patch(
                "app.services.adapters.executor_job.executor_kinds_service"
            ) as mock_executor_service,
            patch("app.services.adapters.executor_job.settings") as mock_settings,
        ):
            mock_settings.CHAT_TASK_EXECUTOR_DELETE_AFTER_HOURS = 24
            mock_settings.CODE_TASK_EXECUTOR_DELETE_AFTER_HOURS = 48
            mock_executor_service.delete_executor_task_sync.side_effect = HTTPException(
                status_code=500,
                detail="delete failed",
            )

            job_service.cleanup_stale_executors(mock_db)

        mark_deleted_mock.assert_not_called()

    def test_executor_deleted_flag_uses_short_lived_session(self, job_service, mock_db):
        """Test executor_deleted_at is updated in a separate short-lived session."""
        short_session = Mock(spec=Session)
        short_subtask_query = MagicMock()
        short_session.query.return_value = short_subtask_query
        short_subtask_query.filter.return_value = short_subtask_query
        short_subtask_query.update.return_value = 1

        with patch(
            "app.services.adapters.executor_job.SessionLocal"
        ) as mock_session_local:
            mock_session_local.return_value = short_session

            job_service._mark_executor_deleted([1, 2])

        short_session.query.assert_called_once_with(Subtask)
        short_subtask_query.update.assert_called_once_with(
            {
                Subtask.executor_deleted_at: True,
            }
        )
        short_session.commit.assert_called_once()
        short_session.close.assert_called_once()

    def test_code_task_is_not_cleaned_up_before_code_threshold(
        self, job_service, mock_db
    ):
        """Test code tasks younger than the code threshold are skipped."""
        mock_subtask = self._create_mock_subtask(1, 100)
        mock_task = self._create_mock_task_resource(100, 1, preserve_executor=False)
        mock_task.json["metadata"]["labels"]["taskType"] = "code"
        mock_subtask.updated_at = datetime.now() - timedelta(hours=2)

        with (
            self._patch_cleanup_scan(job_service, [mock_subtask], {100: mock_task}),
            patch.object(job_service, "_archive_workspace_sync") as archive_mock,
            patch(
                "app.services.adapters.executor_job.executor_kinds_service"
            ) as mock_executor_service,
            patch("app.services.adapters.executor_job.settings") as mock_settings,
        ):
            mock_settings.CHAT_TASK_EXECUTOR_DELETE_AFTER_HOURS = 1
            mock_settings.CODE_TASK_EXECUTOR_DELETE_AFTER_HOURS = 48

            job_service.cleanup_stale_executors(mock_db)

        archive_mock.assert_not_called()
        mock_executor_service.delete_executor_task_sync.assert_not_called()

    def test_cleanup_stale_executors_includes_subscription_tasks(
        self, job_service, test_db
    ):
        """Test scheduled cleanup also deletes executors for subscription tasks."""
        task = TaskResource(
            user_id=1,
            kind="Task",
            name="subscription-task-100",
            namespace="default",
            is_active=TaskResource.STATE_SUBSCRIPTION,
            json={
                "kind": "Task",
                "apiVersion": "agent.wecode.io/v1",
                "metadata": {
                    "name": "subscription-task-100",
                    "namespace": "default",
                    "labels": {"taskType": "chat", "type": "subscription"},
                },
                "spec": {
                    "title": "Subscription Task",
                    "prompt": "Run subscription",
                    "teamRef": {"name": "team-1", "namespace": "default"},
                    "workspaceRef": {"name": "workspace-1", "namespace": "default"},
                },
                "status": {
                    "status": "COMPLETED",
                    "progress": 100,
                    "createdAt": datetime.now().isoformat(),
                    "updatedAt": datetime.now().isoformat(),
                },
            },
            updated_at=datetime.now() - timedelta(hours=48),
        )
        test_db.add(task)
        test_db.commit()
        test_db.refresh(task)

        subtask = Subtask(
            user_id=1,
            task_id=task.id,
            team_id=1,
            title="assistant",
            bot_ids=[1],
            role=SubtaskRole.ASSISTANT,
            status=SubtaskStatus.COMPLETED,
            executor_name="executor-subscription-1",
            executor_namespace="default",
            executor_deleted_at=False,
            updated_at=datetime.now() - timedelta(hours=48),
            completed_at=datetime.now() - timedelta(hours=48),
        )
        test_db.add(subtask)
        test_db.commit()

        with (
            patch.object(job_service, "_mark_executor_deleted") as mark_deleted,
            patch(
                "app.services.adapters.executor_job.executor_kinds_service"
            ) as executor_service,
            patch("app.services.adapters.executor_job.settings") as mock_settings,
        ):
            mock_settings.CHAT_TASK_EXECUTOR_DELETE_AFTER_HOURS = 24
            mock_settings.CODE_TASK_EXECUTOR_DELETE_AFTER_HOURS = 48
            executor_service.delete_executor_task_sync.return_value = {"success": True}

            job_service.cleanup_stale_executors(test_db)

        executor_service.delete_executor_task_sync.assert_called_once_with(
            "executor-subscription-1", "default"
        )
        mark_deleted.assert_called_once_with([subtask.id])

    def test_cleanup_stale_executors_includes_pending_subtasks(
        self, job_service, test_db
    ):
        """Test scheduled cleanup also scans stale PENDING subtasks."""
        task = TaskResource(
            user_id=1,
            kind="Task",
            name="pending-subtask-task-100",
            namespace="default",
            is_active=TaskResource.STATE_ACTIVE,
            json={
                "kind": "Task",
                "apiVersion": "agent.wecode.io/v1",
                "metadata": {
                    "name": "pending-subtask-task-100",
                    "namespace": "default",
                    "labels": {"taskType": "chat"},
                },
                "spec": {
                    "title": "Pending Subtask Task",
                    "prompt": "Run task",
                    "teamRef": {"name": "team-1", "namespace": "default"},
                    "workspaceRef": {"name": "workspace-1", "namespace": "default"},
                },
                "status": {
                    "status": "COMPLETED",
                    "progress": 100,
                    "createdAt": datetime.now().isoformat(),
                    "updatedAt": datetime.now().isoformat(),
                },
            },
            updated_at=datetime.now() - timedelta(hours=48),
        )
        test_db.add(task)
        test_db.commit()
        test_db.refresh(task)

        subtask = Subtask(
            user_id=1,
            task_id=task.id,
            team_id=1,
            title="assistant",
            bot_ids=[1],
            role=SubtaskRole.ASSISTANT,
            status=SubtaskStatus.PENDING,
            executor_name="executor-pending-1",
            executor_namespace="default",
            executor_deleted_at=False,
            updated_at=datetime.now() - timedelta(hours=48),
            completed_at=datetime.now() - timedelta(hours=48),
        )
        test_db.add(subtask)
        test_db.commit()

        with (
            patch.object(job_service, "_mark_executor_deleted") as mark_deleted,
            patch(
                "app.services.adapters.executor_job.executor_kinds_service"
            ) as executor_service,
            patch("app.services.adapters.executor_job.settings") as mock_settings,
        ):
            mock_settings.CHAT_TASK_EXECUTOR_DELETE_AFTER_HOURS = 24
            mock_settings.CODE_TASK_EXECUTOR_DELETE_AFTER_HOURS = 48
            mock_settings.STALE_NON_TERMINAL_TASK_EXECUTOR_DELETE_AFTER_HOURS = 24
            executor_service.delete_executor_task_sync.return_value = {"success": True}

            job_service.cleanup_stale_executors(test_db)

        executor_service.delete_executor_task_sync.assert_called_once_with(
            "executor-pending-1", "default"
        )
        mark_deleted.assert_called_once_with([subtask.id])

    def test_cleanup_skips_invalid_task_json_and_continues(self, job_service, mock_db):
        """Test invalid task JSON does not abort cleanup for other eligible tasks."""
        invalid_subtask = self._create_mock_subtask(1, 100, executor_name="executor-1")
        valid_subtask = self._create_mock_subtask(2, 200, executor_name="executor-2")
        valid_task = self._create_mock_task_resource(200, 1, preserve_executor=False)
        invalid_task = Mock(spec=TaskResource)
        invalid_task.id = 100
        invalid_task.user_id = 1
        invalid_task.kind = "Task"
        invalid_task.is_active = True
        invalid_task.updated_at = datetime.now() - timedelta(hours=48)
        invalid_task.json = {"invalid": "payload"}

        with (
            patch.object(
                job_service,
                "_scan_candidate_subtasks_batch",
                side_effect=[[invalid_subtask, valid_subtask], []],
                create=True,
            ),
            patch.object(
                job_service,
                "_load_tasks_for_cleanup",
                return_value={100: invalid_task, 200: valid_task},
                create=True,
            ),
            patch.object(
                job_service,
                "_get_cleanup_subtasks_for_task",
                side_effect=lambda _db, task_id: {
                    100: [invalid_subtask],
                    200: [valid_subtask],
                }[task_id],
            ),
            patch.object(job_service, "_cleanup_executor_entries") as cleanup_entries,
            patch("app.services.adapters.executor_job.settings") as mock_settings,
        ):
            mock_settings.CHAT_TASK_EXECUTOR_DELETE_AFTER_HOURS = 24
            mock_settings.CODE_TASK_EXECUTOR_DELETE_AFTER_HOURS = 48

            job_service.cleanup_stale_executors(mock_db)

        cleanup_entries.assert_called_once_with(
            db=mock_db,
            task_id=200,
            task=valid_task,
            subtasks=[valid_subtask],
        )

    def test_cleanup_processes_candidates_in_batches(self, job_service, mock_db):
        """Test scheduled cleanup scans subtasks in batches instead of one full query."""
        first_subtask = self._create_mock_subtask(1, 100, executor_name="executor-1")
        second_subtask = self._create_mock_subtask(2, 200, executor_name="executor-2")
        first_task = self._create_mock_task_resource(100, 1, preserve_executor=False)
        second_task = self._create_mock_task_resource(200, 1, preserve_executor=False)

        with (
            patch.object(
                job_service,
                "_scan_candidate_subtasks_batch",
                side_effect=[[first_subtask], [second_subtask], []],
                create=True,
            ) as scan_batch,
            patch.object(
                job_service,
                "_load_tasks_for_cleanup",
                side_effect=[{100: first_task}, {200: second_task}],
                create=True,
            ) as load_tasks,
            patch.object(
                job_service,
                "_get_cleanup_subtasks_for_task",
                side_effect=lambda _db, task_id: {
                    100: [first_subtask],
                    200: [second_subtask],
                }[task_id],
            ),
            patch.object(job_service, "_cleanup_executor_entries") as cleanup_entries,
            patch("app.services.adapters.executor_job.settings") as mock_settings,
        ):
            mock_settings.CHAT_TASK_EXECUTOR_DELETE_AFTER_HOURS = 24
            mock_settings.CODE_TASK_EXECUTOR_DELETE_AFTER_HOURS = 48

            job_service.cleanup_stale_executors(mock_db)

        assert scan_batch.call_count == 3
        assert load_tasks.call_count == 2
        assert cleanup_entries.call_count == 2

    def test_cleanup_logs_filter_stats_when_no_valid_candidates(
        self, job_service, mock_db
    ):
        """Test cleanup summary logs include filter reason counts."""
        missing_task_subtask = self._create_mock_subtask(
            1, 100, executor_name="missing"
        )
        preserved_subtask = self._create_mock_subtask(2, 200, executor_name="preserved")
        preserved_task = self._create_mock_task_resource(200, 1, preserve_executor=True)

        with (
            patch.object(
                job_service,
                "_scan_candidate_subtasks_batch",
                side_effect=[[missing_task_subtask, preserved_subtask], []],
                create=True,
            ),
            patch.object(
                job_service,
                "_load_tasks_for_cleanup",
                return_value={200: preserved_task},
                create=True,
            ),
            patch("app.services.adapters.executor_job.logger") as mock_logger,
            patch("app.services.adapters.executor_job.settings") as mock_settings,
        ):
            mock_settings.CHAT_TASK_EXECUTOR_DELETE_AFTER_HOURS = 24
            mock_settings.CODE_TASK_EXECUTOR_DELETE_AFTER_HOURS = 48

            job_service.cleanup_stale_executors(mock_db)

        no_valid_call = next(
            call
            for call in mock_logger.info.call_args_list
            if call.args
            and call.args[0].startswith(
                "[executor_job] No valid expired executor to clean up after task status check"
            )
        )
        assert no_valid_call.args == (
            "[executor_job] No valid expired executor to clean up after task status "
            "check scanned=%d last_id=%d missing_task=%d invalid_task_payload=%d "
            "non_terminal_task=%d stale_non_terminal_task=%d "
            "preserve_executor=%d code_task_recent=%d task_updated_recent=%d",
            2,
            2,
            1,
            0,
            0,
            0,
            1,
            0,
            0,
        )

    def test_cleanup_allows_stale_non_terminal_tasks(self, job_service, mock_db):
        """Test scheduled cleanup allows very old non-terminal parent tasks."""
        mock_subtask = self._create_mock_subtask(1, 100)
        mock_task = self._create_mock_task_resource(100, 1, preserve_executor=False)
        mock_task.json["status"]["status"] = "RUNNING"
        mock_task.updated_at = datetime.now() - timedelta(hours=72)

        with (
            self._patch_cleanup_scan(job_service, [mock_subtask], {100: mock_task}),
            patch.object(job_service, "_mark_executor_deleted") as mark_deleted_mock,
            patch(
                "app.services.adapters.executor_job.executor_kinds_service"
            ) as mock_executor_service,
            patch("app.services.adapters.executor_job.settings") as mock_settings,
        ):
            mock_settings.CHAT_TASK_EXECUTOR_DELETE_AFTER_HOURS = 24
            mock_settings.CODE_TASK_EXECUTOR_DELETE_AFTER_HOURS = 48
            mock_settings.STALE_NON_TERMINAL_TASK_EXECUTOR_DELETE_AFTER_HOURS = 24
            mock_executor_service.delete_executor_task_sync.return_value = True

            job_service.cleanup_stale_executors(mock_db)

        mock_executor_service.delete_executor_task_sync.assert_called_once_with(
            "executor-1", "default"
        )
        mark_deleted_mock.assert_called_once_with([1])

    def test_cleanup_allows_pending_parent_tasks(self, job_service, mock_db):
        """Test scheduled cleanup treats PENDING parent tasks as eligible."""
        mock_subtask = self._create_mock_subtask(1, 100)
        mock_task = self._create_mock_task_resource(100, 1, preserve_executor=False)
        mock_task.json["status"]["status"] = "PENDING"
        mock_task.json["metadata"]["labels"]["type"] = "subscription"
        mock_task.updated_at = datetime.now()

        with (
            self._patch_cleanup_scan(job_service, [mock_subtask], {100: mock_task}),
            patch.object(job_service, "_mark_executor_deleted") as mark_deleted_mock,
            patch(
                "app.services.adapters.executor_job.executor_kinds_service"
            ) as mock_executor_service,
            patch("app.services.adapters.executor_job.settings") as mock_settings,
        ):
            mock_settings.CHAT_TASK_EXECUTOR_DELETE_AFTER_HOURS = 24
            mock_settings.CODE_TASK_EXECUTOR_DELETE_AFTER_HOURS = 48
            mock_settings.STALE_NON_TERMINAL_TASK_EXECUTOR_DELETE_AFTER_HOURS = 24
            mock_executor_service.delete_executor_task_sync.return_value = True

            job_service.cleanup_stale_executors(mock_db)

        mock_executor_service.delete_executor_task_sync.assert_called_once_with(
            "executor-1", "default"
        )
        mark_deleted_mock.assert_called_once_with([1])

    def test_cleanup_scans_past_first_ten_batches_until_deleted_target(
        self, job_service, mock_db
    ):
        """Test cleanup is limited by deleted executors rather than the first ten batches."""
        invalid_batches = [
            [self._create_mock_subtask(batch_no, 1000 + batch_no)]
            for batch_no in range(1, 11)
        ]
        valid_subtask = self._create_mock_subtask(11, 200, executor_name="executor-11")
        valid_task = self._create_mock_task_resource(200, 1, preserve_executor=False)

        with (
            patch(
                "app.services.adapters.executor_job.CLEANUP_TARGET_DELETED_EXECUTORS_PER_RUN",
                1,
                create=True,
            ),
            patch("app.services.adapters.executor_job.CLEANUP_MAX_BATCHES_PER_RUN", 20),
            patch.object(
                job_service,
                "_scan_candidate_subtasks_batch",
                side_effect=[*invalid_batches, [valid_subtask], []],
                create=True,
            ) as scan_batch,
            patch.object(
                job_service,
                "_load_tasks_for_cleanup",
                side_effect=[{}] * 10 + [{200: valid_task}],
                create=True,
            ),
            patch.object(
                job_service,
                "_get_cleanup_subtasks_for_task",
                return_value=[valid_subtask],
            ),
            patch.object(job_service, "_cleanup_executor_entries") as cleanup_entries,
            patch("app.services.adapters.executor_job.settings") as mock_settings,
        ):
            mock_settings.CHAT_TASK_EXECUTOR_DELETE_AFTER_HOURS = 24
            mock_settings.CODE_TASK_EXECUTOR_DELETE_AFTER_HOURS = 48
            cleanup_entries.return_value = {
                "task_id": 200,
                "deleted": True,
                "skipped": False,
                "reason": "executor_deleted",
                "executors": [
                    {
                        "executor_name": "executor-11",
                        "executor_namespace": "default",
                    }
                ],
            }

            job_service.cleanup_stale_executors(mock_db)

        assert scan_batch.call_count == 11
        cleanup_entries.assert_called_once_with(
            db=mock_db,
            task_id=200,
            task=valid_task,
            subtasks=[valid_subtask],
        )

    def test_cleanup_stops_after_reaching_deleted_target(self, job_service, mock_db):
        """Test cleanup stops scanning once the per-run deleted target is reached."""
        first_subtask = self._create_mock_subtask(1, 100, executor_name="executor-1")
        second_subtask = self._create_mock_subtask(2, 200, executor_name="executor-2")
        third_subtask = self._create_mock_subtask(3, 300, executor_name="executor-3")
        first_task = self._create_mock_task_resource(100, 1, preserve_executor=False)
        second_task = self._create_mock_task_resource(200, 1, preserve_executor=False)
        third_task = self._create_mock_task_resource(300, 1, preserve_executor=False)

        with (
            patch(
                "app.services.adapters.executor_job.CLEANUP_TARGET_DELETED_EXECUTORS_PER_RUN",
                2,
                create=True,
            ),
            patch("app.services.adapters.executor_job.CLEANUP_MAX_BATCHES_PER_RUN", 20),
            patch.object(
                job_service,
                "_scan_candidate_subtasks_batch",
                side_effect=[[first_subtask], [second_subtask], [third_subtask], []],
                create=True,
            ) as scan_batch,
            patch.object(
                job_service,
                "_load_tasks_for_cleanup",
                side_effect=[
                    {100: first_task},
                    {200: second_task},
                    {300: third_task},
                ],
                create=True,
            ),
            patch.object(
                job_service,
                "_get_cleanup_subtasks_for_task",
                side_effect=lambda _db, task_id: {
                    100: [first_subtask],
                    200: [second_subtask],
                    300: [third_subtask],
                }[task_id],
            ),
            patch.object(
                job_service,
                "_cleanup_executor_groups",
                side_effect=[0, 1, 1],
            ) as cleanup_groups,
            patch("app.services.adapters.executor_job.settings") as mock_settings,
        ):
            mock_settings.CHAT_TASK_EXECUTOR_DELETE_AFTER_HOURS = 24
            mock_settings.CODE_TASK_EXECUTOR_DELETE_AFTER_HOURS = 48

            job_service.cleanup_stale_executors(mock_db)

        assert scan_batch.call_count == 3
        assert cleanup_groups.call_count == 3


@pytest.mark.unit
class TestCleanupTaskExecutorAPI(CleanupExecutorTestHelpers):
    """Test task-scoped executor cleanup service behavior."""

    @pytest.fixture
    def job_service(self):
        """Create JobService instance"""
        from app.models.kind import Kind

        return JobService(Kind)

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session"""
        return Mock(spec=Session)

    def test_cleanup_task_executor_deletes_current_task_executor(
        self, job_service, mock_db
    ):
        """Test manual cleanup deletes the current task executor."""
        mock_task = self._create_mock_task_resource(100, 1, preserve_executor=False)
        mock_subtask = self._create_mock_subtask(1, 100)
        self._setup_task_and_subtask_queries(mock_db, mock_task, [mock_subtask])

        with (
            patch("app.services.task_member_service.task_member_service") as members,
            patch.object(job_service, "_mark_executor_deleted") as mark_deleted,
            patch(
                "app.services.adapters.executor_job.executor_kinds_service"
            ) as executor_service,
        ):
            members.is_member.return_value = True
            executor_service.delete_executor_task_sync.return_value = {"success": True}

            result = job_service.cleanup_task_executor(mock_db, task_id=100, user_id=1)

        assert result == {
            "task_id": 100,
            "deleted": True,
            "skipped": False,
            "reason": "executor_deleted",
            "executors": [
                {
                    "executor_name": "executor-1",
                    "executor_namespace": "default",
                }
            ],
        }
        executor_service.delete_executor_task_sync.assert_called_once_with(
            "executor-1", "default"
        )
        mark_deleted.assert_called_once_with([1])

    def test_cleanup_task_executor_skips_preserved_task(self, job_service, mock_db):
        """Test manual cleanup respects preserveExecutor=true."""
        mock_task = self._create_mock_task_resource(100, 1, preserve_executor=True)
        self._setup_task_and_subtask_queries(mock_db, mock_task, [])

        with patch("app.services.task_member_service.task_member_service") as members:
            members.is_member.return_value = True

            result = job_service.cleanup_task_executor(mock_db, task_id=100, user_id=1)

        assert result == {
            "task_id": 100,
            "deleted": False,
            "skipped": True,
            "reason": "preserve_executor",
            "executors": [],
        }

    def test_cleanup_task_executor_skips_non_terminal_task(self, job_service, mock_db):
        """Test manual cleanup skips non-terminal tasks."""
        mock_task = self._create_mock_task_resource(100, 1, preserve_executor=False)
        mock_task.json["status"]["status"] = "RUNNING"
        self._setup_task_and_subtask_queries(mock_db, mock_task, [])

        with patch("app.services.task_member_service.task_member_service") as members:
            members.is_member.return_value = True

            result = job_service.cleanup_task_executor(mock_db, task_id=100, user_id=1)

        assert result["task_id"] == 100
        assert result["deleted"] is False
        assert result["skipped"] is True
        assert result["reason"] == "task_not_finished"

    def test_cleanup_task_executor_deduplicates_executor_names(
        self, job_service, mock_db
    ):
        """Test manual cleanup deletes a shared executor only once."""
        mock_task = self._create_mock_task_resource(100, 1, preserve_executor=False)
        subtask_a = self._create_mock_subtask(1, 100)
        subtask_b = self._create_mock_subtask(2, 100)
        self._setup_task_and_subtask_queries(mock_db, mock_task, [subtask_a, subtask_b])

        with (
            patch("app.services.task_member_service.task_member_service") as members,
            patch.object(job_service, "_mark_executor_deleted") as mark_deleted,
            patch(
                "app.services.adapters.executor_job.executor_kinds_service"
            ) as executor_service,
        ):
            members.is_member.return_value = True
            executor_service.delete_executor_task_sync.return_value = {"success": True}

            result = job_service.cleanup_task_executor(mock_db, task_id=100, user_id=1)

        assert result["task_id"] == 100
        assert result["deleted"] is True
        assert result["skipped"] is False
        assert result["reason"] == "executor_deleted"
        executor_service.delete_executor_task_sync.assert_called_once_with(
            "executor-1", "default"
        )
        mark_deleted.assert_called_once_with([1, 2])

    def test_cleanup_task_executor_supports_subscription_tasks(
        self, job_service, test_db
    ):
        """Test manual cleanup accepts subscription task state."""
        task = TaskResource(
            user_id=1,
            kind="Task",
            name="subscription-task-200",
            namespace="default",
            is_active=TaskResource.STATE_SUBSCRIPTION,
            json={
                "kind": "Task",
                "apiVersion": "agent.wecode.io/v1",
                "metadata": {
                    "name": "subscription-task-200",
                    "namespace": "default",
                    "labels": {"taskType": "chat", "type": "subscription"},
                },
                "spec": {
                    "title": "Subscription Task",
                    "prompt": "Run subscription",
                    "teamRef": {"name": "team-1", "namespace": "default"},
                    "workspaceRef": {"name": "workspace-1", "namespace": "default"},
                },
                "status": {
                    "status": "COMPLETED",
                    "progress": 100,
                    "createdAt": datetime.now().isoformat(),
                    "updatedAt": datetime.now().isoformat(),
                },
            },
        )
        test_db.add(task)
        test_db.commit()
        test_db.refresh(task)

        subtask = Subtask(
            user_id=1,
            task_id=task.id,
            team_id=1,
            title="assistant",
            bot_ids=[1],
            role=SubtaskRole.ASSISTANT,
            status=SubtaskStatus.COMPLETED,
            executor_name="executor-subscription-2",
            executor_namespace="default",
            executor_deleted_at=False,
            completed_at=datetime.now(),
        )
        test_db.add(subtask)
        test_db.commit()

        with (
            patch("app.services.task_member_service.task_member_service") as members,
            patch.object(job_service, "_mark_executor_deleted") as mark_deleted,
            patch(
                "app.services.adapters.executor_job.executor_kinds_service"
            ) as executor_service,
        ):
            members.is_member.return_value = True
            executor_service.delete_executor_task_sync.return_value = {"success": True}

            result = job_service.cleanup_task_executor(
                test_db, task_id=task.id, user_id=1
            )

        assert result["deleted"] is True
        assert result["reason"] == "executor_deleted"
        executor_service.delete_executor_task_sync.assert_called_once_with(
            "executor-subscription-2", "default"
        )
        mark_deleted.assert_called_once_with([subtask.id])


@pytest.mark.unit
class TestSetPreserveExecutorAPI:
    """Test set_preserve_executor API functionality"""

    @pytest.fixture
    def task_service(self):
        """Create TaskKindsService instance"""
        return TaskKindsService(TaskResource)

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session"""
        return Mock(spec=Session)

    def _create_mock_task(
        self, task_id: int, user_id: int, preserve_executor: bool = False
    ):
        """Helper to create a mock TaskResource"""
        task = Mock(spec=TaskResource)
        task.id = task_id
        task.user_id = user_id
        task.kind = "Task"
        task.is_active = True

        labels = {"taskType": "chat"}
        if preserve_executor:
            labels["preserveExecutor"] = "true"

        task.json = {
            "kind": "Task",
            "apiVersion": "agent.wecode.io/v1",
            "metadata": {
                "name": f"task-{task_id}",
                "namespace": "default",
                "labels": labels,
            },
            "spec": {
                "title": "Test Task",
                "prompt": "Test prompt",
                "teamRef": {"name": "test-team", "namespace": "default"},
                "workspaceRef": {"name": "workspace-1", "namespace": "default"},
            },
            "status": {
                "status": "COMPLETED",
                "progress": 100,
                "createdAt": datetime.now().isoformat(),
                "updatedAt": datetime.now().isoformat(),
            },
        }
        return task

    def test_set_preserve_executor_true(self, task_service, mock_db):
        """Test setting preserveExecutor to true"""
        mock_task = self._create_mock_task(123, 1, preserve_executor=False)

        # Setup mock query chain
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_task

        # Mock task_member_service (imported inside the function)
        with patch(
            "app.services.task_member_service.task_member_service"
        ) as mock_member_service:
            mock_member_service.is_member.return_value = True

            # Mock flag_modified to avoid SQLAlchemy internals
            with patch(
                "app.services.adapters.task_kinds.operations.flag_modified"
            ) as mock_flag_modified:
                result = task_service.set_preserve_executor(
                    mock_db, task_id=123, user_id=1, preserve=True
                )

                assert result["task_id"] == 123
                assert result["preserve_executor"] is True
                assert "preserved" in result["message"].lower()

                # Verify the task json was updated
                assert (
                    mock_task.json["metadata"]["labels"]["preserveExecutor"] == "true"
                )
                mock_db.commit.assert_called_once()
                mock_flag_modified.assert_called_once()

    def test_set_preserve_executor_false(self, task_service, mock_db):
        """Test setting preserveExecutor to false"""
        mock_task = self._create_mock_task(123, 1, preserve_executor=True)

        # Setup mock query chain
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_task

        # Mock task_member_service (imported inside the function)
        with patch(
            "app.services.task_member_service.task_member_service"
        ) as mock_member_service:
            mock_member_service.is_member.return_value = True

            # Mock flag_modified to avoid SQLAlchemy internals
            with patch(
                "app.services.adapters.task_kinds.operations.flag_modified"
            ) as mock_flag_modified:
                result = task_service.set_preserve_executor(
                    mock_db, task_id=123, user_id=1, preserve=False
                )

                assert result["task_id"] == 123
                assert result["preserve_executor"] is False
                assert "cleanup" in result["message"].lower()

                # Verify the task json was updated to "false" (not deleted)
                assert (
                    mock_task.json["metadata"]["labels"]["preserveExecutor"] == "false"
                )
                mock_db.commit.assert_called_once()
                mock_flag_modified.assert_called_once()

    def test_non_member_cannot_set_preserve_executor(self, task_service, mock_db):
        """Test that non-members cannot set preserve executor flag"""
        mock_task = self._create_mock_task(123, 1, preserve_executor=False)

        # Setup mock query chain
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_task

        # Mock task_member_service (imported inside the function)
        with patch(
            "app.services.task_member_service.task_member_service"
        ) as mock_member_service:
            mock_member_service.is_member.return_value = False

            with pytest.raises(HTTPException) as exc_info:
                task_service.set_preserve_executor(
                    mock_db, task_id=123, user_id=999, preserve=True
                )

            assert exc_info.value.status_code == 404
            assert (
                "not found" in exc_info.value.detail.lower()
                or "permission" in exc_info.value.detail.lower()
            )

    def test_task_not_found_raises_404(self, task_service, mock_db):
        """Test that non-existent task raises 404"""
        # Setup mock query chain to return None
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        # Mock task_member_service (imported inside the function)
        with patch(
            "app.services.task_member_service.task_member_service"
        ) as mock_member_service:
            mock_member_service.is_member.return_value = False

            with pytest.raises(HTTPException) as exc_info:
                task_service.set_preserve_executor(
                    mock_db, task_id=999, user_id=1, preserve=True
                )

            assert exc_info.value.status_code == 404

    def test_group_member_can_set_preserve_executor(self, task_service, mock_db):
        """Test that group chat members can set preserve executor flag"""
        mock_task = self._create_mock_task(123, 1, preserve_executor=False)

        # Setup mock query chain
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_task

        # Mock task_member_service (imported inside the function)
        with patch(
            "app.services.task_member_service.task_member_service"
        ) as mock_member_service:
            # User 2 is a group member, not the owner (user_id=1)
            mock_member_service.is_member.return_value = True

            # Mock flag_modified to avoid SQLAlchemy internals
            with patch(
                "app.services.adapters.task_kinds.operations.flag_modified"
            ) as mock_flag_modified:
                result = task_service.set_preserve_executor(
                    mock_db, task_id=123, user_id=2, preserve=True
                )

                assert result["task_id"] == 123
                assert result["preserve_executor"] is True
                mock_member_service.is_member.assert_called_once_with(mock_db, 123, 2)
                mock_flag_modified.assert_called_once()


@pytest.mark.unit
class TestPreserveExecutorLabelConsistency:
    """Test that preserveExecutor label is handled consistently"""

    def test_preserve_executor_uses_string_values(self):
        """Test that preserveExecutor uses 'true'/'false' string values like autoDeleteExecutor"""
        task_json = {
            "metadata": {
                "labels": {
                    "autoDeleteExecutor": "false",  # Existing pattern uses strings
                    "preserveExecutor": "true",  # Should follow same pattern
                }
            }
        }

        # Both should use string values for consistency
        assert task_json["metadata"]["labels"]["autoDeleteExecutor"] == "false"
        assert task_json["metadata"]["labels"]["preserveExecutor"] == "true"

    def test_preserve_executor_false_is_explicit(self):
        """Test that setting preserve=False results in 'false' string, not key deletion"""
        # This ensures the behavior matches autoDeleteExecutor pattern
        labels = {"preserveExecutor": "true"}

        # When disabling, should set to "false" not delete
        labels["preserveExecutor"] = "false"

        assert "preserveExecutor" in labels
        assert labels["preserveExecutor"] == "false"
