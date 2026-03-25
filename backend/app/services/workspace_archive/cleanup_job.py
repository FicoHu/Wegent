# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
Cleanup job for expired workspace archives.

Runs daily to remove expired archive files from MinIO
and clean up archive metadata from Task status.
"""

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.task import TaskResource
from app.schemas.kind import Task

from .storage import ARCHIVE_ENABLED, archive_storage_service

logger = logging.getLogger(__name__)


def cleanup_expired_archives(db: Session) -> int:
    """Clean up expired workspace archives.

    Scans all tasks with archive info and:
    1. Deletes archive files from MinIO if expired
    2. Clears archive metadata from Task.status

    Args:
        db: Database session

    Returns:
        Number of archives cleaned up
    """
    if not ARCHIVE_ENABLED:
        logger.info("[ArchiveCleanup] Archiving is disabled, skipping cleanup")
        return 0

    logger.info("[ArchiveCleanup] Starting expired archive cleanup")
    cleaned_count = 0
    error_count = 0

    try:
        # Query all active tasks
        tasks = (
            db.query(TaskResource)
            .filter(
                TaskResource.kind == "Task",
                TaskResource.is_active == TaskResource.STATE_ACTIVE,
            )
            .all()
        )

        now = datetime.utcnow()

        for task in tasks:
            try:
                task_crd = Task.model_validate(task.json)
                archive_info = task_crd.status.archive if task_crd.status else None

                # Skip if no archive
                if not archive_info or not archive_info.storageKey:
                    continue

                # Check if expired
                if not archive_info.expiresAt:
                    continue

                if archive_info.expiresAt >= now:
                    # Not yet expired
                    continue

                logger.info(
                    f"[ArchiveCleanup] Cleaning up expired archive for task {task.id}, "
                    f"expired at {archive_info.expiresAt}"
                )

                # Delete from MinIO
                deleted = archive_storage_service.delete_archive(
                    archive_info.storageKey
                )

                if deleted:
                    # Clear archive info from task
                    task_json = task.json
                    if "status" in task_json and "archive" in task_json["status"]:
                        del task_json["status"]["archive"]
                        task.json = task_json
                        db.add(task)

                    cleaned_count += 1
                    logger.info(
                        f"[ArchiveCleanup] Cleaned up archive for task {task.id}"
                    )
                else:
                    # Archive file may not exist, still clear metadata
                    task_json = task.json
                    if "status" in task_json and "archive" in task_json["status"]:
                        del task_json["status"]["archive"]
                        task.json = task_json
                        db.add(task)
                    cleaned_count += 1
                    logger.warning(
                        f"[ArchiveCleanup] Archive file not found for task {task.id}, "
                        "cleared metadata only"
                    )

            except Exception as e:
                error_count += 1
                logger.error(
                    f"[ArchiveCleanup] Error processing task {task.id}: {e}",
                    exc_info=True,
                )
                continue

        db.commit()

        logger.info(
            f"[ArchiveCleanup] Completed: cleaned={cleaned_count}, errors={error_count}"
        )
        return cleaned_count

    except Exception as e:
        logger.error(f"[ArchiveCleanup] Error during cleanup: {e}", exc_info=True)
        db.rollback()
        return 0
