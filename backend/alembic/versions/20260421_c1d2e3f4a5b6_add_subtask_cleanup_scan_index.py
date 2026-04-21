# SPDX-FileCopyrightText: 2026 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""add_subtask_cleanup_scan_index

Revision ID: c1d2e3f4a5b6
Revises: a1b2c3d4e5f6
Create Date: 2026-04-21

Add a composite index that supports scheduled executor cleanup scans over
completed subtasks with undeleted executors.
"""

import sqlalchemy as sa

from alembic import op

revision = "c1d2e3f4a5b6"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the subtask cleanup scan index if it does not exist."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("subtasks")}

    if "idx_subtasks_cleanup_scan" not in existing_indexes:
        op.create_index(
            "idx_subtasks_cleanup_scan",
            "subtasks",
            ["executor_deleted_at", "status", "updated_at", "task_id", "id"],
        )


def downgrade() -> None:
    """Drop the subtask cleanup scan index if it exists."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("subtasks")}

    if "idx_subtasks_cleanup_scan" in existing_indexes:
        op.drop_index("idx_subtasks_cleanup_scan", table_name="subtasks")
