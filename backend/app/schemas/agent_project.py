# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
AgentProject schemas for API request/response validation.

AgentProjects are development projects with execution environment configuration.
Each task created within an AgentProject inherits its configuration.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TeamRef(BaseModel):
    """Team reference model."""

    name: str = Field(..., description="Team name")
    namespace: str = Field(default="default", description="Team namespace")
    user_id: int = Field(..., description="Team owner user ID")


class WorkspaceRef(BaseModel):
    """Workspace reference model."""

    name: str = Field(..., description="Workspace name")
    namespace: str = Field(default="default", description="Workspace namespace")


class AgentProjectTaskResponse(BaseModel):
    """Response model for a task within an agent project."""

    task_id: int = Field(..., description="Task ID")
    task_title: str = Field(..., description="Task title")
    task_status: str = Field(..., description="Task status")
    created_at: datetime = Field(..., description="Task creation time")

    class Config:
        from_attributes = True


class AgentProjectBase(BaseModel):
    """Base model for agent project data."""

    name: str = Field(..., min_length=1, max_length=100, description="Project name")
    description: Optional[str] = Field(default="", description="Project description")
    environment_type: str = Field(
        default="cloud_docker",
        description="Execution environment: cloud_docker, local_device, cloud_device",
    )
    directory_path: Optional[str] = Field(default=None, description="Working directory path")
    git_url: Optional[str] = Field(default=None, description="Git repository URL")
    git_repo: Optional[str] = Field(default=None, description="Git repository name")
    git_branch: Optional[str] = Field(default="main", description="Git branch name")
    device_id: Optional[str] = Field(default=None, description="Device ID")


class AgentProjectCreate(AgentProjectBase):
    """Request model for creating an agent project."""

    team_ref: TeamRef = Field(..., description="Team reference")


class AgentProjectUpdate(BaseModel):
    """Request model for updating an agent project."""

    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    environment_type: Optional[str] = Field(
        None,
        description="Execution environment: cloud_docker, local_device, cloud_device",
    )
    team_ref: Optional[TeamRef] = Field(None, description="Team reference")
    directory_path: Optional[str] = Field(None, description="Working directory path")
    git_url: Optional[str] = Field(None, description="Git repository URL")
    git_repo: Optional[str] = Field(None, description="Git repository name")
    git_branch: Optional[str] = Field(None, description="Git branch name")
    device_id: Optional[str] = Field(None, description="Device ID")


class AgentProjectResponse(AgentProjectBase):
    """Response model for an agent project."""

    id: int = Field(..., description="Project ID")
    user_id: int = Field(..., description="Project owner user ID")
    team_ref: TeamRef = Field(..., description="Team reference")
    workspace_ref: WorkspaceRef = Field(..., description="Workspace reference")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class AgentProjectWithTasksResponse(AgentProjectResponse):
    """Response model for an agent project with its tasks."""

    tasks: list[AgentProjectTaskResponse] = Field(
        default_factory=list,
        description="Tasks in this project",
    )


class AgentProjectListResponse(BaseModel):
    """Response model for agent project list."""

    total: int = Field(..., description="Total number of projects")
    items: list[AgentProjectWithTasksResponse] = Field(
        default_factory=list,
        description="List of projects",
    )


class CreateTaskFromProjectRequest(BaseModel):
    """Request model for creating a task from an agent project."""

    prompt: str = Field(..., description="User prompt")
    title: Optional[str] = Field(None, description="Task title")
