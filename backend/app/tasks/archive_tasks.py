# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
Celery tasks for workspace archive operations.

This module provides Celery tasks for:
1. Expired archive cleanup (scheduled daily)
"""

import logging

from app.core.celery_app import celery_app
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.archive_tasks.cleanup_expired_archives",
    max_retries=1,
    default_retry_delay=300,
)
def cleanup_expired_archives_task(self):
    """
    Celery task for cleaning up expired workspace archives.

    This task runs daily at 3:00 AM to:
    1. Find all archives that have expired (>30 days old)
    2. Delete archive files from MinIO
    3. Clear archive metadata from Task.status

    The task is scheduled by Celery Beat.
    """
    task_id = getattr(self.request, "id", "unknown")
    retry_count = getattr(self.request, "retries", 0)

    logger.info(
        f"[Celery Archive Cleanup] Task started: task_id={task_id}, "
        f"retry={retry_count}/{self.max_retries}"
    )

    db = SessionLocal()
    try:
        from app.services.workspace_archive.cleanup_job import cleanup_expired_archives

        cleaned_count = cleanup_expired_archives(db)

        logger.info(
            f"[Celery Archive Cleanup] Completed: task_id={task_id}, "
            f"cleaned_count={cleaned_count}"
        )

        return {
            "status": "success",
            "cleaned_count": cleaned_count,
        }

    except Exception as e:
        logger.error(
            f"[Celery Archive Cleanup] Error: task_id={task_id}, "
            f"retry={retry_count}/{self.max_retries}, error={e}",
            exc_info=True,
        )
        raise self.retry(exc=e)

    finally:
        db.close()
