"""Pydantic schemas for the streaming material sync API.

Design
------
The sync protocol works in three stages:

1.  Client sends   GET /api/v1/materials/stream
        ?since=<ISO-8601 UTC>          (0 on first run → full catalog)
        &batch_size=<100-200>          (number of records per SSE event)
        &cursor=<opaque string>        (resume token after a disconnect)

2.  Server streams back newline-delimited SSE events:

        data: {"event": "batch", "cursor": "...", "total": 1200,
               "offset": 0, "count": 150, "materials": [...]}

        data: {"event": "batch", "cursor": "...", "total": 1200,
               "offset": 150, "count": 150, "materials": [...]}

        ...

        data: {"event": "complete", "server_timestamp": "2024-...",
               "total_sent": 1200, "inserted": 1100, "updated": 100,
               "deleted_ids": ["id1", "id2"]}

3.  If the connection is dropped mid-stream the client reconnects and
    includes the last received `cursor` value.  The server resumes from
    exactly that point — no records are re-sent, none are skipped.

Cursor encoding
---------------
The cursor is a base64-encoded JSON string containing:
    {"since": "<ISO-8601>", "offset": <int>}

It is intentionally opaque to the client; only the server produces and
interprets it.  The client stores it and passes it back on reconnect.
"""
from __future__ import annotations

import base64
import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Wire types
# ---------------------------------------------------------------------------

class SyncBatchEvent(BaseModel):
    """A single SSE data frame carrying a batch of materials.

    Sent repeatedly until all matching rows have been streamed.
    """
    event: str = "batch"
    cursor: str = Field(
        ...,
        description="Opaque resume token.  Store and send back on reconnect.",
    )
    total: int = Field(..., ge=0, description="Total rows matched by the query.")
    offset: int = Field(..., ge=0, description="Zero-based offset of this batch's first row.")
    count: int = Field(..., ge=0, description="Number of records in this batch.")
    materials: list[dict[str, Any]] = Field(default_factory=list)


class SyncCompleteEvent(BaseModel):
    """Final SSE frame — signals that all records have been streamed.

    The client must advance its local `lastSyncTimestamp` to
    `server_timestamp` only after receiving this frame so that partial
    syncs are detected on the next launch and resumed automatically.
    """
    event: str = "complete"
    server_timestamp: str = Field(
        ...,
        description="ISO-8601 UTC timestamp to use as `since` on the next sync.",
    )
    total_sent: int = Field(..., ge=0)
    inserted: int = Field(..., ge=0, description="New rows the client should insert.")
    updated: int = Field(..., ge=0, description="Existing rows the client should update.")
    deleted_ids: list[str] = Field(
        default_factory=list,
        description="Material IDs that were soft-deleted since `since`.",
    )


class SyncErrorEvent(BaseModel):
    """Emitted as the final SSE frame when the server encounters an error.

    Clients should NOT advance the sync cursor on receiving this event;
    instead they should schedule an automatic retry with exponential backoff.
    """
    event: str = "error"
    code: str
    message: str
    retryable: bool = True


# ---------------------------------------------------------------------------
# Query parameters
# ---------------------------------------------------------------------------

class SyncQueryParams(BaseModel):
    """Validated query parameters for the streaming sync endpoint."""

    since: str = Field(
        default="1970-01-01T00:00:00Z",
        description="ISO-8601 UTC datetime.  Only rows with updated_at > since are returned.",
    )
    batch_size: int = Field(
        default=150,
        ge=10,
        le=500,
        description="Records per SSE batch.  Recommended: 100-200.",
    )
    cursor: str | None = Field(
        default=None,
        description="Resume token from the last received batch event.  Null on first attempt.",
    )

    @field_validator("since")
    @classmethod
    def validate_since(cls, v: str) -> str:
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"since must be ISO-8601 UTC: {exc}") from exc
        return v


# ---------------------------------------------------------------------------
# Cursor codec
# ---------------------------------------------------------------------------

class SyncCursor:
    """Encode and decode the opaque resume cursor.

    Schema versions
    ---------------
    v1 (legacy LIMIT/OFFSET):
        {"since": "<ISO-8601>", "offset": <int>}

    v2 (keyset — current):
        {"v": 2, "since": "<ISO-8601>", "last_ts": "<ISO-8601>",
         "last_poly": "<str>", "offset": -1}

    Both are base64url-encoded so they are safe as URL query parameters.
    The v1 ``encode``/``decode`` methods are kept for backward compatibility
    with any in-flight sync sessions.  New sessions use the keyset cursor
    helpers in materials_stream.py directly.
    """

    @staticmethod
    def encode(since_iso: str, offset: int) -> str:
        """Encode a v1 LIMIT/OFFSET cursor (kept for backward compatibility)."""
        payload = json.dumps({"since": since_iso, "offset": offset}, separators=(",", ":"))
        return base64.urlsafe_b64encode(payload.encode()).decode()

    @staticmethod
    def decode(token: str) -> tuple[str, int]:
        """Return (since_iso, offset) from a v1 cursor, or raise ValueError.

        For v2 keyset cursors this returns (since_iso, -1) — callers that
        only handle v1 should treat offset==-1 as "use keyset resume".
        """
        try:
            payload = base64.urlsafe_b64decode(token.encode() + b"==").decode()
            data = json.loads(payload)
            if not isinstance(data, dict) or "since" not in data or ("offset" not in data and "v" not in data):
                raise ValueError("Missing required fields in cursor payload")
            return str(data["since"]), int(data.get("offset", -1))
        except Exception as exc:
            raise ValueError(f"Invalid sync cursor: {exc}") from exc


# ---------------------------------------------------------------------------
# Legacy schemas (kept for backwards compatibility — existing /sync endpoint)
# ---------------------------------------------------------------------------

class MaterialSyncResponse(BaseModel):
    """Legacy full-catalog sync response.  Retained for API versioning."""
    materials: list[Any]
    server_timestamp: datetime
