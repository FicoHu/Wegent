# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
AgentProject service for managing development projects.

AgentProjects are independent from the existing Project (dialog grouping) model.
Each project binds to a Team, Workspace, and optional Device.
"""

import logging
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.agent_project import AgentProject
from app.models.task import TaskResource
from app.schemas.agent_project import (
    AgentProjectCreate,
    AgentProjectListResponse,
    AgentProjectResponse,
    AgentProjectTaskResponse,
    AgentProjectUpdate,
    AgentProjectWithTasksResponse,
    TeamRef,
    WorkspaceRef,
)

logger = logging.getLogger(__name__)


def _get_project_tasks(db: Session, project_id: int, user_id: int) -> list[AgentProjectTaskResponse]:
    """Get all tasks in an agent project."""
    from app.schemas.kind import Task as TaskCRD

    tasks = (
        db.query(TaskResource)
        .filter(
            TaskResource.user_id == user_id,
            TaskResource.kind == "Task",
            TaskResource.is_active == TaskResource.STATE_ACTIVE,
        )
        .order_by(TaskResource.created_at.desc())
        .all()
    )

    result = []
    for task in tasks:
        try:
            task_crd = TaskCRD.model_validate(task.json)
            # Check if task belongs to this project via workspaceRef
            if (
                task_crd.spec.workspaceRef
                and task_crd.spec.workspaceRef.name == f"workspace-project-{project_id}"
            ):
                result.append(
                    AgentProjectTaskResponse(
                        task_id=task.id,
                        task_title=task_crd.spec.title or f"Task #{task.id}",
                        task_status=task_crd.status.status if task_crd.status else "PENDING",
                        created_at=task.created_at,
                    )
                )
        except Exception:
            continue

    return result


def create_agent_project(
    db: Session,
    project_data: AgentProjectCreate,
    user_id: int,
) -> AgentProjectWithTasksResponse:
    """Create a new agent project with an associated Workspace CRD."""
    # Validate team_ref
    team_ref = project_data.team_ref

    # Create the AgentProject record first to get the ID
    new_project = AgentProject(
        user_id=user_id,
        name=project_data.name,
        description=project_data.description,
        environment_type=project_data.environment_type,
        team_ref=team_ref.model_dump(),
        workspace_ref={"name": "", "namespace": "default"},
        directory_path=project_data.directory_path,
        git_url=project_data.git_url,
        git_repo=project_data.git_repo,
        git_branch=project_data.git_branch,
        device_id=project_data.device_id,
        is_active=True,
    )
    db.add(new_project)
    db.flush()  # Flush to get the ID

    # Create Workspace CRD
    workspace_name = f"workspace-project-{new_project.id}"
    workspace_json = {
        "kind": "Workspace",
        "spec": {
            "repository": {
                "gitUrl": project_data.git_url,
                "gitRepo": project_data.git_repo,
                "gitDomain": None,
                "branchName": project_data.git_branch,
            }
        },
        "status": {"state": "Available"},
        "metadata": {"name": workspace_name, "namespace": "default"},
        "apiVersion": "agent.wecode.io/v1",
    }

    workspace = TaskResource(
        user_id=user_id,
        kind="Workspace",
        name=workspace_name,
        namespace="default",
        json=workspace_json,
        is_active=True,
    )
    db.add(workspace)

    # Update project workspace_ref
    new_project.workspace_ref = {"name": workspace_name, "namespace": "default"}
    db.commit()
    db.refresh(new_project)

    return AgentProjectWithTasksResponse(
        id=new_project.id,
        user_id=new_project.user_id,
        name=new_project.name,
        description=new_project.description or "",
        environment_type=new_project.environment_type,
        team_ref=TeamRef.model_validate(new_project.team_ref),
        workspace_ref=WorkspaceRef.model_validate(new_project.workspace_ref),
        directory_path=new_project.directory_path,
        git_url=new_project.git_url,
        git_repo=new_project.git_repo,
        git_branch=new_project.git_branch,
        device_id=new_project.device_id,
        created_at=new_project.created_at,
        updated_at=new_project.updated_at,
        tasks=[],
    )


def get_agent_project(
    db: Session,
    project_id: int,
    user_id: int,
) -> Optional[AgentProjectWithTasksResponse]:
    """Get an agent project by ID with its tasks."""
    project = (
        db.query(AgentProject)
        .filter(
            AgentProject.id == project_id,
            AgentProject.user_id == user_id,
            AgentProject.is_active == True,
        )
        .first()
    )

    if not project:
        return None

    tasks = _get_project_tasks(db, project_id, user_id)

    return AgentProjectWithTasksResponse(
        id=project.id,
        user_id=project.user_id,
        name=project.name,
        description=project.description or "",
        environment_type=project.environment_type,
        team_ref=TeamRef.model_validate(project.team_ref),
        workspace_ref=WorkspaceRef.model_validate(project.workspace_ref),
        directory_path=project.directory_path,
        git_url=project.git_url,
        git_repo=project.git_repo,
        git_branch=project.git_branch,
        device_id=project.device_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
        tasks=tasks,
    )


def list_agent_projects(
    db: Session,
    user_id: int,
) -> AgentProjectListResponse:
    """List all agent projects for a user."""
    projects = (
        db.query(AgentProject)
        .filter(
            AgentProject.user_id == user_id,
            AgentProject.is_active == True,
        )
        .order_by(AgentProject.created_at.desc())
        .all()
    )

    items = []
    for project in projects:
        tasks = _get_project_tasks(db, project.id, user_id)
        items.append(
            AgentProjectWithTasksResponse(
                id=project.id,
                user_id=project.user_id,
                name=project.name,
                description=project.description or "",
                environment_type=project.environment_type,
                team_ref=TeamRef.model_validate(project.team_ref),
                workspace_ref=WorkspaceRef.model_validate(project.workspace_ref),
                directory_path=project.directory_path,
                git_url=project.git_url,
                git_repo=project.git_repo,
                git_branch=project.git_branch,
                device_id=project.device_id,
                created_at=project.created_at,
                updated_at=project.updated_at,
                tasks=tasks,
            )
        )

    return AgentProjectListResponse(total=len(items), items=items)


def update_agent_project(
    db: Session,
    project_id: int,
    update_data: AgentProjectUpdate,
    user_id: int,
) -> AgentProjectWithTasksResponse:
    """Update an agent project."""
    project = (
        db.query(AgentProject)
        .filter(
            AgentProject.id == project_id,
            AgentProject.user_id == user_id,
            AgentProject.is_active == True,
        )
        .first()
    )

    if not project:
        raise HTTPException(status_code=404, detail="Agent project not found")

    update_dict = update_data.model_dump(exclude_unset=True)

    # Update project fields
    for field, value in update_dict.items():
        if field in ("team_ref",) and value is not None:
            value = value.model_dump() if hasattr(value, "model_dump") else value
        if hasattr(project, field):
            setattr(project, field, value)

    # Update workspace if git-related fields changed
    if any(field in update_dict for field in ("git_url", "git_repo", "git_branch")):
        workspace = (
            db.query(TaskResource)
            .filter(
                TaskResource.user_id == user_id,
                TaskResource.kind == "Workspace",
                TaskResource.name == project.workspace_ref["name"],
                TaskResource.namespace == project.workspace_ref["namespace"],
                TaskResource.is_active == TaskResource.STATE_ACTIVE,
            )
            .first()
        )
        if workspace and workspace.json:
            from app.schemas.kind import Workspace as WorkspaceCRD

            workspace_crd = WorkspaceCRD.model_validate(workspace.json)
            if "git_url" in update_dict:
                workspace_crd.spec.repository.gitUrl = update_dict["git_url"]
            if "git_repo" in update_dict:
                workspace_crd.spec.repository.gitRepo = update_dict["git_repo"]
            if "git_branch" in update_dict:
                workspace_crd.spec.repository.branchName = update_dict["git_branch"]
            workspace.json = workspace_crd.model_dump(mode="json", exclude_none=True)
            from sqlalchemy.orm.attributes import flag_modified

            flag_modified(workspace, "json")

    db.commit()
    db.refresh(project)

    tasks = _get_project_tasks(db, project_id, user_id)

    return AgentProjectWithTasksResponse(
        id=project.id,
        user_id=project.user_id,
        name=project.name,
        description=project.description or "",
        environment_type=project.environment_type,
        team_ref=TeamRef.model_validate(project.team_ref),
        workspace_ref=WorkspaceRef.model_validate(project.workspace_ref),
        directory_path=project.directory_path,
        git_url=project.git_url,
        git_repo=project.git_repo,
        git_branch=project.git_branch,
        device_id=project.device_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
        tasks=tasks,
    )


def delete_agent_project(db: Session, project_id: int, user_id: int) -> None:
    """Soft delete an agent project.

    Tasks are not deleted; their workspaceRef remains pointing to the
    project workspace for historical reference.
    """
    project = (
        db.query(AgentProject)
        .filter(
            AgentProject.id == project_id,
            AgentProject.user_id == user_id,
            AgentProject.is_active == True,
        )
        .first()
    )

    if not project:
        raise HTTPException(status_code=404, detail="Agent project not found")

    project.is_active = False
    db.commit()
