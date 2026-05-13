# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
AgentProject model for managing development projects with execution environment.

AgentProjects are independent from the existing Project (dialog grouping) model.
Each AgentProject binds to a Team, Workspace, and optional Device.
Tasks created within an AgentProject share the project's Workspace and configuration.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.sql import func

from app.db.base import Base


class AgentProject(Base):
    """
    AgentProject model for development projects.

    Each project binds to a Team (agent), Workspace, and optional Device.
    Tasks created within the project inherit its configuration.
    """

    __tablename__ = "agent_projects"

    id = Column(Integer, primary_key=True, index=True, comment="Primary key")
    user_id = Column(
        Integer,
        nullable=False,
        index=True,
        comment="Project owner user ID",
    )
    name = Column(
        String(100),
        nullable=False,
        comment="Project name",
    )
    description = Column(
        Text,
        nullable=True,
        default=None,
        comment="Project description",
    )
    environment_type = Column(
        String(20),
        nullable=False,
        default="cloud_docker",
        comment="Execution environment: cloud_docker, local_device, cloud_device",
    )
    team_ref = Column(
        JSON,
        nullable=False,
        comment="Team reference: {name, namespace, user_id}",
    )
    workspace_ref = Column(
        JSON,
        nullable=False,
        comment="Workspace reference: {name, namespace}",
    )
    directory_path = Column(
        String(500),
        nullable=True,
        default=None,
        comment="Working directory path",
    )
    git_url = Column(
        String(500),
        nullable=True,
        default=None,
        comment="Git repository URL",
    )
    git_repo = Column(
        String(200),
        nullable=True,
        default=None,
        comment="Git repository name",
    )
    git_branch = Column(
        String(100),
        nullable=True,
        default="main",
        comment="Git branch name",
    )
    device_id = Column(
        String(100),
        nullable=True,
        default=None,
        comment="Device ID for local_device or cloud_device",
    )
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Soft delete marker",
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        comment="Creation timestamp",
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
        comment="Last update timestamp",
    )

    __table_args__ = (
        {
            "sqlite_autoincrement": True,
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_unicode_ci",
            "comment": "Agent projects table for development project management",
        },
    )
