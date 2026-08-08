"""Projects API — CRUD + delta sync.

requirements and results are persisted as JSON strings (LONGTEXT) in MySQL.
The API layer serialises dicts to JSON before writing and deserialises on read.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.project import Project
from app.models.user import User
from app.auth.dependencies import require_auth
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectSyncResponse,
)

router = APIRouter(prefix="/projects", tags=["Projects"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_json(value: dict | None) -> str | None:
    if value is None:
        return None
    return json.dumps(value, default=str)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """List the authenticated user's non-deleted projects."""
    result = await db.execute(
        select(Project)
        .where(Project.user_id == user.id, Project.is_deleted.is_(False))
        .offset(skip)
        .limit(limit)
        .order_by(Project.updated_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Create a new project, or upsert an existing one by client-supplied ID."""
    now = _now()

    if project_in.id:
        # Client-supplied ID — check for existing record (offline sync scenario)
        result = await db.execute(
            select(Project).where(
                Project.id == project_in.id,
                Project.user_id == user.id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            # Last-write-wins merge
            existing.title = project_in.title
            existing.requirements_json = _to_json(project_in.requirements) or "{}"
            existing.results_json = _to_json(project_in.results)
            existing.updated_at = now
            existing.is_deleted = False
            await db.flush()
            return existing

    project = Project(
        id=project_in.id or str(uuid.uuid4()),
        user_id=user.id,
        title=project_in.title,
        requirements_json=_to_json(project_in.requirements) or "{}",
        results_json=_to_json(project_in.results),
        created_at=now,
        updated_at=now,
    )
    db.add(project)
    await db.flush()
    return project


@router.get("/sync", response_model=ProjectSyncResponse)
async def sync_projects(
    since: datetime = Query(..., description="ISO timestamp — return projects updated after this"),
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Delta sync — return all projects (including soft-deleted) updated after [since]."""
    result = await db.execute(
        select(Project)
        .where(Project.user_id == user.id, Project.updated_at > since)
        .order_by(Project.updated_at)
    )
    return ProjectSyncResponse(
        projects=result.scalars().all(),
        server_timestamp=_now(),
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Fetch a single project by ID."""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == user.id,
            Project.is_deleted.is_(False),
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_in: ProjectUpdate,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Update title, requirements, and/or results of an existing project."""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == user.id,
            Project.is_deleted.is_(False),
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if project_in.title is not None:
        project.title = project_in.title
    if project_in.requirements is not None:
        project.requirements_json = _to_json(project_in.requirements) or "{}"
    if project_in.results is not None:
        project.results_json = _to_json(project_in.results)
    project.updated_at = _now()

    await db.flush()
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a project (recoverable via sync)."""
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    project.is_deleted = True
    project.updated_at = _now()
    await db.flush()
