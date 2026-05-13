# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
AgentProject API endpoints for managing development projects.

AgentProjects are independent from the existing Project (dialog grouping) model.
Each project binds to a Team, Workspace, and optional Device.
"""

from fastapi import APIRouter, Body, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.agent_project import (
    AgentProjectCreate,
    AgentProjectListResponse,
    AgentProjectResponse,
    AgentProjectUpdate,
    AgentProjectWithTasksResponse,
    CreateTaskFromProjectRequest,
)
from app.services import agent_project_service
from app.services.adapters.task_kinds import task_kinds_service

router = APIRouter()


@router.get("", response_model=AgentProjectListResponse)
def list_agent_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all agent projects for the current user."""
    return agent_project_service.list_agent_projects(
        db=db, user_id=current_user.id
    )


@router.post("", response_model=AgentProjectWithTasksResponse, status_code=status.HTTP_201_CREATED)
def create_agent_project_endpoint(
    project_create: AgentProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new agent project.

    Automatically creates a Workspace CRD (workspace-project-{id}).
    """
    try:
        return agent_project_service.create_agent_project(
            db=db, project_data=project_create, user_id=current_user.id
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create agent project: {str(e)}",
        )


@router.get("/{project_id}", response_model=AgentProjectWithTasksResponse)
def get_agent_project_endpoint(
    project_id: int = Path(..., description="Project ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get agent project details by ID with its tasks."""
    project = agent_project_service.get_agent_project(
        db=db, project_id=project_id, user_id=current_user.id
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent project not found",
        )

    return project


@router.put("/{project_id}", response_model=AgentProjectWithTasksResponse)
def update_agent_project_endpoint(
    project_id: int = Path(..., description="Project ID"),
    project_update: AgentProjectUpdate = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update agent project information."""
    try:
        return agent_project_service.update_agent_project(
            db=db,
            project_id=project_id,
            update_data=project_update,
            user_id=current_user.id,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update agent project: {str(e)}",
        )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent_project_endpoint(
    project_id: int = Path(..., description="Project ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an agent project (soft delete).

    Tasks are not deleted; their workspaceRef remains for historical reference.
    """
    try:
        agent_project_service.delete_agent_project(
            db=db, project_id=project_id, user_id=current_user.id
        )
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete agent project: {str(e)}",
        )


@router.post("/{project_id}/tasks", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_task_from_project(
    project_id: int = Path(..., description="Project ID"),
    request: CreateTaskFromProjectRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new task within an agent project.

    The task inherits the project's Team, Workspace, and Device configuration.
    """
    from app.schemas.task import TaskCreate

    project = agent_project_service.get_agent_project(
        db=db, project_id=project_id, user_id=current_user.id
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent project not found",
        )

    task_create = TaskCreate(
        title=request.title,
        prompt=request.prompt,
        team_name=project.team_ref.name,
        team_namespace=project.team_ref.namespace,
        type="online",
        task_type="code",
        source="web",
    )

    result = task_kinds_service.create_task_or_append(
        db=db,
        obj_in=task_create,
        user=current_user,
        project_id=project_id,
    )

    return result
