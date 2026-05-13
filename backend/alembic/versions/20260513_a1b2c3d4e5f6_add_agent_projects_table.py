# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Add agent_projects table

Revision ID: 20260513_a1b2c3d4e5f6
Revises: 20260428_b2c3d4e5f707
Create Date: 2026-05-13 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260513_a1b2c3d4e5f6"
down_revision: Union[str, None] = "20260428_b2c3d4e5f707"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - create agent_projects table."""
    op.create_table(
        "agent_projects",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False, index=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "environment_type",
            sa.String(length=20),
            nullable=False,
            server_default="cloud_docker",
        ),
        sa.Column("team_ref", sa.JSON(), nullable=False),
        sa.Column("workspace_ref", sa.JSON(), nullable=False),
        sa.Column("directory_path", sa.String(length=500), nullable=True),
        sa.Column("git_url", sa.String(length=500), nullable=True),
        sa.Column("git_repo", sa.String(length=200), nullable=True),
        sa.Column("git_branch", sa.String(length=100), nullable=True),
        sa.Column("device_id", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )


def downgrade() -> None:
    """Downgrade schema - drop agent_projects table."""
    op.drop_table("agent_projects")
