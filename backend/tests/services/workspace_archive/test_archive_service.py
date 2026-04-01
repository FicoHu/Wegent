# SPDX-FileCopyrightText: 2026 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for workspace archive service time handling."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services.workspace_archive import archive_service


def _build_task(expires_at: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=22,
        json={
            "apiVersion": "agent.wecode.io/v1",
            "kind": "Task",
            "metadata": {
                "name": "task-22",
                "namespace": "default",
            },
            "spec": {
                "title": "task-22",
                "prompt": "resume task",
                "teamRef": {
                    "name": "team-1",
                    "namespace": "default",
                },
                "workspaceRef": {
                    "name": "workspace-1",
                    "namespace": "default",
                },
            },
            "status": {
                "archive": {
                    "storageKey": "workspace-archives/22/archive.tar.gz",
                    "expiresAt": expires_at,
                }
            },
        },
    )


def test_check_archive_available_supports_legacy_naive_expiration():
    """Legacy naive timestamps should still be recognized as expired."""
    expires_at = (datetime.utcnow() - timedelta(days=1)).isoformat()
    task = _build_task(expires_at)

    available, storage_key, reason = archive_service.check_archive_available(task)

    assert available is False
    assert storage_key is None
    assert reason == "expired"


@pytest.mark.asyncio
async def test_restore_workspace_supports_legacy_naive_expiration():
    """Restore should safely reject expired legacy timestamps without type errors."""
    expires_at = (datetime.utcnow() - timedelta(days=1)).isoformat()
    task = _build_task(expires_at)

    result = await archive_service.restore_workspace(
        db=MagicMock(),
        task=task,
        executor_name="executor-22",
        executor_namespace="default",
    )

    assert result is False


def test_check_archive_available_supports_utc_aware_expiration():
    """Timezone-aware UTC timestamps should remain available before expiry."""
    expires_at = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    task = _build_task(expires_at)

    available, storage_key, reason = archive_service.check_archive_available(task)

    assert available is True
    assert storage_key == "workspace-archives/22/archive.tar.gz"
    assert reason is None
