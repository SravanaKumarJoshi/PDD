"""Pydantic schemas for Projects.

requirements and results are stored as JSON strings in MySQL (LONGTEXT).
The API accepts/returns them as plain dicts — serialisation happens here.
"""

from __future__ import annotations

import json
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator


class ProjectCreate(BaseModel):
    id: str | None = None          # client may supply own UUID for offline-sync
    title: str = Field(..., min_length=1, max_length=255)
    requirements: dict = Field(default_factory=dict)
    results: dict | None = None


class ProjectUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    requirements: dict | None = None
    results: dict | None = None


class ProjectResponse(BaseModel):
    id: str
    user_id: str
    title: str
    requirements: dict = Field(default_factory=dict)
    results: dict | None = None
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def parse_json_columns(cls, values):
        """Convert requirements_json / results_json TEXT columns → dicts."""
        if hasattr(values, "__dict__"):
            # SQLAlchemy ORM object
            obj = values
            data = {
                "id": str(obj.id),
                "user_id": str(obj.user_id),
                "title": obj.title,
                "created_at": obj.created_at,
                "updated_at": obj.updated_at,
                "is_deleted": obj.is_deleted,
                "requirements": _safe_json(getattr(obj, "requirements_json", "{}")),
                "results": _safe_json(getattr(obj, "results_json", None)),
            }
            return data
        return values


class ProjectSyncResponse(BaseModel):
    projects: list[ProjectResponse]
    server_timestamp: datetime


def _safe_json(value: str | None) -> dict | None:
    if not value:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None
