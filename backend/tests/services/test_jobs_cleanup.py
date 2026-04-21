# SPDX-FileCopyrightText: 2026 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for cleanup worker coordination."""

from contextlib import contextmanager
from unittest.mock import Mock, patch

import pytest

from app.services.jobs import cleanup_worker


@contextmanager
def _lock_context(acquired: bool):
    yield acquired


@pytest.mark.unit
def test_cleanup_worker_skips_when_lock_is_held():
    """Test cleanup worker does not run cleanup without acquiring the lock."""
    stop_event = Mock()
    stop_event.is_set.side_effect = [False, True]

    with (
        patch(
            "app.services.jobs.distributed_lock.acquire_watchdog_context",
            return_value=_lock_context(False),
            create=True,
        ),
        patch("app.services.jobs.job_service.cleanup_stale_executors") as cleanup_mock,
        patch("app.services.jobs.SessionLocal") as session_local,
    ):
        cleanup_worker(stop_event)

    cleanup_mock.assert_not_called()
    session_local.assert_not_called()
