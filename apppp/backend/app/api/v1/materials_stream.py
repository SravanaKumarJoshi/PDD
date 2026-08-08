"""Streaming material synchronization endpoint.

Architecture
------------
This module implements the production-grade, offline-first synchronization
endpoint that replaces the legacy ``GET /api/v1/materials/sync`` bulk-load
approach.

Key design decisions
~~~~~~~~~~~~~~~~~~~~
1. **Server-Sent Events (SSE)** — The server pushes records to the client
   incrementally.  The connection stays open until all matching rows have
   been delivered.  Because SSE is unidirectional (server → client) and
   built on HTTP/1.1, it works through every proxy and firewall that allows
   standard HTTP responses.

2. **Keyset (cursor) pagination** — Instead of LIMIT N OFFSET K, every page
   uses ``WHERE (updated_at, polymer) > (:last_ts, :last_poly)`` so MySQL
   performs an index seek rather than a full scan-and-discard.  With
   LIMIT/OFFSET the 200th batch (offset=30 000) forces MySQL to read and
   throw away 30 000 rows on each query; keyset pagination makes every page
   equally fast regardless of position.

   Every SSE ``batch`` frame carries an opaque cursor that encodes
   ``(since, last_updated_at, last_polymer)``.  If the connection is dropped
   the client reconnects with that cursor and the server resumes in O(log N)
   — no duplicates, no gaps, no full-table scans.

3. **Delta sync** — The ``since`` parameter means the server only queries
   ``WHERE updated_at > :since``, so incremental syncs return near-zero rows
   on a quiet catalog.  The server returns an immediate ``complete`` frame
   rather than streaming empty batches.

4. **Soft deletes** — Materials that were removed since the last sync are
   returned in the ``deleted_ids`` field of the ``complete`` frame so the
   client can mark them as deleted locally without a separate API call.

5. **Memory efficiency** — Rows are fetched in ``batch_size`` chunks.  The
   generator never holds the entire result set in memory.

6. **Backpressure** — ``asyncio.sleep(0)`` yields the event loop between
   batches so long-running streams do not monopolise the async worker.

7. **No COUNT(*) per batch** — The total-row count is queried once at stream
   start (before the first batch).  Pagination advances via the keyset cursor,
   not by re-computing ``OFFSET``, so there are no redundant COUNT scans.

Performance requirements (verified by these design decisions)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- First byte sent within 1–2 seconds (count query + first batch query).
- Subsequent batches: O(log N) per page via index seek, not O(N).
- Memory: O(batch_size) at any point, never O(total_rows).
- 100 K+ rows: no degradation — each page hits the composite index
  ``(updated_at, polymer)``.

Security
~~~~~~~~
- ``since`` must be a valid ISO-8601 UTC string.
- ``batch_size`` is capped at 500 (default 150).
- Rate limiting is inherited from the global slowapi middleware.

Required index
~~~~~~~~~~~~~~
    CREATE INDEX IF NOT EXISTS idx_fp_updated_at_polymer
        ON filtered_polymers (updated_at ASC, polymer ASC);

See ``scripts/migrations/add_sync_indexes.sql``.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, Query, Request, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.material import MaterialPropertySchema, MaterialResponse
from app.schemas.sync import SyncCursor, SyncBatchEvent, SyncCompleteEvent, SyncErrorEvent
from app.sync_metrics import SyncMetrics, make_request_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/materials", tags=["Materials Sync"])

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Minimum allowed batch size
MIN_BATCH_SIZE: int = 10

#: Maximum allowed batch size (hard cap — prevents memory exhaustion)
MAX_BATCH_SIZE: int = 500

#: Default batch size (balanced between latency and throughput)
DEFAULT_BATCH_SIZE: int = 150

#: Yield the event loop between batches to avoid blocking the async worker
INTER_BATCH_SLEEP_S: float = 0.0

#: SSE keep-alive comment emitted every N seconds to prevent proxy timeouts.
#: Set to 15 s — well below nginx's default proxy_read_timeout of 60 s and
#: the typical 30 s idle-connection timeout seen on AWS ALB / GCP LB.
SSE_KEEPALIVE_INTERVAL_S: float = 15.0

#: Warn if any single operation (query, serialisation) exceeds this threshold.
SLOW_OPERATION_THRESHOLD_MS: float = 500.0


# ---------------------------------------------------------------------------
# Row → response helpers
# ---------------------------------------------------------------------------

def _as_material(row: dict, now: datetime) -> MaterialResponse:
    """Convert a raw DB row to a MaterialResponse."""
    primary_key = row.get("polymer") or row.get("id") or "unknown"
    bio = row.get("biocompatibility") or 0
    updated_at = row.get("updated_at") or now
    if not isinstance(updated_at, datetime):
        updated_at = now
    return MaterialResponse(
        id=str(primary_key),
        name=str(primary_key),
        category=str(row.get("category") or "unknown"),
        source=row.get("source_doi"),
        notes=None,
        evidence_level=row.get("evidence_level") or "low",
        references=[],
        ext_properties={"primary_key": str(primary_key)},
        created_at=updated_at,
        updated_at=updated_at,
        properties=MaterialPropertySchema(
            tensile_strength_mpa_min=row.get("tensile_strength"),
            tensile_strength_mpa_max=row.get("tensile_strength"),
            elastic_modulus_gpa_min=row.get("elastic_modulus"),
            elastic_modulus_gpa_max=row.get("elastic_modulus"),
            elongation_pct_min=row.get("elongation_pct"),
            elongation_pct_max=row.get("elongation_pct"),
            wvtr=row.get("wvtr"),
            otr=row.get("oxygen_permeability"),
            degradation_days_min=row.get("biodegradation_days"),
            degradation_days_max=row.get("biodegradation_days"),
            cytotoxicity_safe=(bio >= 7),
            hemocompatible=(bio >= 7),
            antimicrobial=bool(row.get("antimicrobial")),
            ster_gamma=bool(row.get("sterilization_gamma")),
            ster_eto=bool(row.get("sterilization_eto")),
            ster_steam=bool(row.get("sterilization_steam")),
            proc_film=bool(row.get("film_forming")),
            solvent_compatible=row.get("solubility"),
            cost_band=row.get("cost_band"),
            availability_band=row.get("availability_band"),
            data_completeness=float(row.get("data_completeness") or 0),
        ),
    )


# ---------------------------------------------------------------------------
# SSE frame helpers
# ---------------------------------------------------------------------------

def _sse_data(payload: dict) -> str:
    """Format a single SSE ``data:`` frame.

    SSE spec requires each frame to be terminated with ``\\n\\n``.
    """
    return f"data: {json.dumps(payload, default=str)}\n\n"


def _sse_keepalive() -> str:
    """SSE comment frame — keeps the connection alive through idle proxies."""
    return ": keepalive\n\n"


def _warn_slow(label: str, elapsed_ms: float, request_id: str) -> None:
    """Emit a WARNING log when any operation exceeds SLOW_OPERATION_THRESHOLD_MS."""
    if elapsed_ms > SLOW_OPERATION_THRESHOLD_MS:
        logger.warning(
            "stream_sync | SLOW_OP | requestId=%s | op=%s | elapsed_ms=%.1f",
            request_id, label, elapsed_ms,
        )


# ---------------------------------------------------------------------------
# Keyset cursor helpers
# ---------------------------------------------------------------------------

def _keyset_cursor_encode(since_iso: str, last_ts: str, last_polymer: str) -> str:
    """Encode (since_iso, last_updated_at, last_polymer) into an opaque cursor.

    The cursor is stored in base64url so it is safe as a URL query parameter.
    ``SyncCursor.encode`` stores (since_iso, offset) for backward compatibility
    with the old LIMIT/OFFSET scheme; we extend the schema here with the
    keyset fields and keep the ``offset`` field set to -1 so any legacy decoder
    can detect it is a keyset cursor and ignore offset.
    """
    import base64
    payload = json.dumps(
        {
            "v": 2,                  # cursor schema version
            "since": since_iso,
            "last_ts": last_ts,
            "last_poly": last_polymer,
            "offset": -1,            # sentinel: not an offset cursor
        },
        separators=(",", ":"),
    )
    return base64.urlsafe_b64encode(payload.encode()).decode()


def _keyset_cursor_decode(token: str) -> tuple[str, str | None, str | None, int]:
    """Decode a cursor token.

    Returns
    -------
    (since_iso, last_ts, last_polymer, offset)
    - For v2 keyset cursors: last_ts and last_polymer are set, offset == -1.
    - For legacy v1 LIMIT/OFFSET cursors: last_ts and last_polymer are None,
      offset >= 0.
    """
    import base64
    try:
        raw = base64.urlsafe_b64decode(token.encode() + b"==").decode()
        data = json.loads(raw)
    except Exception as exc:
        raise ValueError(f"Invalid sync cursor: {exc}") from exc

    since_iso = str(data["since"])
    version = data.get("v", 1)

    if version == 2:
        return (
            since_iso,
            str(data["last_ts"]),
            str(data["last_poly"]),
            -1,
        )
    else:
        # Legacy v1 LIMIT/OFFSET cursor — resume from that offset (one-time
        # compatibility path so existing clients mid-sync don't lose progress).
        return since_iso, None, None, int(data.get("offset", 0))


# ---------------------------------------------------------------------------
# Core streaming generator
# ---------------------------------------------------------------------------

async def _stream_sync(
    db: AsyncSession,
    since_iso: str,
    batch_size: int,
    request_id: str,
    # Keyset resume position (v2 cursor)
    resume_last_ts: str | None = None,
    resume_last_polymer: str | None = None,
    # Legacy LIMIT/OFFSET resume position (v1 cursor, one-time compatibility)
    legacy_start_offset: int = 0,
) -> AsyncGenerator[str, None]:
    """Yield SSE frames for all materials whose updated_at > since.

    Pagination strategy: keyset (cursor) pagination
    ------------------------------------------------
    Instead of LIMIT N OFFSET K (which forces MySQL to scan K rows to find
    the start of each page), we use a composite keyset condition:

        WHERE updated_at > :since
          AND (updated_at, polymer) > (:last_ts, :last_poly)
        ORDER BY updated_at ASC, polymer ASC
        LIMIT :batch_size

    This means:
    - Page 1: no keyset condition (first batch after :since).
    - Page 2+: keyset is set to (updated_at, polymer) of the last row of the
      previous batch.
    - MySQL performs an index seek directly to the right position, O(log N),
      regardless of how deep into the result set we are.
    - No COUNT(*) is needed per batch.

    The total COUNT(*) is still done once at stream start so the client can
    display a progress bar.  This single count query is cheap and cached for
    the duration of the stream.

    Yields
    ------
    str
        SSE-formatted strings ready to be sent as response bytes.
    """
    stream_start_ns = time.perf_counter_ns()
    now = datetime.now(timezone.utc)

    metrics = SyncMetrics(
        request_id=request_id,
        since_iso=since_iso,
        batch_size=batch_size,
    )
    metrics.log_start()

    try:
        since_dt = datetime.fromisoformat(since_iso.replace("Z", "+00:00"))
    except ValueError:
        since_dt = datetime(1970, 1, 1, tzinfo=timezone.utc)

    # ── Step 1: count matching rows (done ONCE — not per batch) ──────────
    count_t0 = time.perf_counter_ns()
    try:
        count_result = await db.execute(
            text(
                "SELECT COUNT(*) FROM filtered_polymers "  # noqa: S608
                "WHERE updated_at > :since"
            ),
            {"since": since_dt},
        )
        total: int = count_result.scalar() or 0
        count_ms = (time.perf_counter_ns() - count_t0) / 1_000_000.0
        metrics.log_total_known(total)
        logger.info(
            "stream_sync | event=count | requestId=%s | total=%d | count_ms=%.1f",
            request_id, total, count_ms,
        )
        _warn_slow("count_query", count_ms, request_id)
    except Exception as exc:
        metrics.log_error("db_count_failed", str(exc))
        yield _sse_data(
            SyncErrorEvent(
                code="db_count_failed",
                message="Could not determine sync batch count.",
            ).model_dump()
        )
        return

    # Short-circuit: nothing to sync
    if total == 0:
        metrics.log_empty()
        yield _sse_data(
            SyncCompleteEvent(
                server_timestamp=now.isoformat(),
                total_sent=0,
                inserted=0,
                updated=0,
                deleted_ids=[],
            ).model_dump()
        )
        return

    # ── Step 2: stream batches via keyset pagination ──────────────────────
    deleted_ids: list[str] = []
    last_keepalive = time.perf_counter()
    first_byte_sent = False
    offset_counter = 0          # logical offset for display/logging only
    has_more = True

    # Keyset position: updated_at + polymer of the last row seen.
    # None means "start from the beginning".
    keyset_last_ts: str | None = resume_last_ts
    keyset_last_polymer: str | None = resume_last_polymer

    # Legacy LIMIT/OFFSET compatibility: if client sent a v1 cursor we do
    # one OFFSET-based page to land at the right position, then switch to
    # keyset from there.
    use_legacy_offset: bool = legacy_start_offset > 0
    legacy_offset: int = legacy_start_offset

    while has_more:
        # Emit keepalive to prevent proxy timeouts on slow queries
        now_perf = time.perf_counter()
        if now_perf - last_keepalive > SSE_KEEPALIVE_INTERVAL_S:
            yield _sse_keepalive()
            last_keepalive = time.perf_counter()

        metrics.begin_batch()
        query_t0 = time.perf_counter_ns()

        try:
            if use_legacy_offset:
                # One-time LIMIT/OFFSET page for legacy cursor resume
                result = await db.execute(
                    text(
                        "SELECT *, COALESCE(is_deleted, 0) AS _is_deleted_flag "
                        "FROM filtered_polymers "  # noqa: S608
                        "WHERE updated_at > :since "
                        "ORDER BY updated_at ASC, polymer ASC "
                        "LIMIT :limit OFFSET :offset"
                    ),
                    {
                        "since": since_dt,
                        "limit": batch_size,
                        "offset": legacy_offset,
                    },
                )
                use_legacy_offset = False  # switch to keyset from next batch
            elif keyset_last_ts is None:
                # First page — no keyset condition, just the since filter
                result = await db.execute(
                    text(
                        "SELECT *, COALESCE(is_deleted, 0) AS _is_deleted_flag "
                        "FROM filtered_polymers "  # noqa: S608
                        "WHERE updated_at > :since "
                        "ORDER BY updated_at ASC, polymer ASC "
                        "LIMIT :limit"
                    ),
                    {"since": since_dt, "limit": batch_size},
                )
            else:
                # Subsequent pages — keyset seek: O(log N) regardless of depth
                #
                # The condition (updated_at > :last_ts) OR
                #               (updated_at = :last_ts AND polymer > :last_poly)
                # is equivalent to the tuple comparison (updated_at, polymer) > (:last_ts, :last_poly)
                # but written explicitly for maximum MySQL optimizer compatibility.
                result = await db.execute(
                    text(
                        "SELECT *, COALESCE(is_deleted, 0) AS _is_deleted_flag "
                        "FROM filtered_polymers "  # noqa: S608
                        "WHERE updated_at > :since "
                        "  AND ("
                        "    updated_at > :last_ts "
                        "    OR (updated_at = :last_ts AND polymer > :last_poly)"
                        "  ) "
                        "ORDER BY updated_at ASC, polymer ASC "
                        "LIMIT :limit"
                    ),
                    {
                        "since": since_dt,
                        "limit": batch_size,
                        "last_ts": keyset_last_ts,
                        "last_poly": keyset_last_polymer,
                    },
                )

            rows = result.mappings().all()

        except Exception as exc:
            query_ms = (time.perf_counter_ns() - query_t0) / 1_000_000.0
            metrics.log_error("db_fetch_failed", str(exc), offset=offset_counter)
            yield _sse_data(
                SyncErrorEvent(
                    code="db_fetch_failed",
                    message=f"Failed to fetch batch at offset {offset_counter}. Retry with cursor.",
                ).model_dump()
            )
            return

        query_ms = (time.perf_counter_ns() - query_t0) / 1_000_000.0
        _warn_slow(f"batch_query@{offset_counter}", query_ms, request_id)

        if not rows:
            # No more rows — we're done
            has_more = False
            break

        # Separate active from soft-deleted records
        active_rows: list[dict] = []
        batch_deleted: list[str] = []
        last_row_dict: dict | None = None

        for row in rows:
            row_dict = dict(row)
            is_del = row_dict.pop("_is_deleted_flag", row_dict.get("is_deleted", 0))
            if is_del:
                pk = row_dict.get("polymer") or row_dict.get("id")
                if pk:
                    batch_deleted.append(str(pk))
            else:
                active_rows.append(row_dict)
            last_row_dict = row_dict  # track last row for keyset advancement

        deleted_ids.extend(batch_deleted)
        materials = [_as_material(r, now) for r in active_rows]

        # Advance keyset cursor to the last row in this batch
        if last_row_dict is not None:
            raw_ts = last_row_dict.get("updated_at")
            if isinstance(raw_ts, datetime):
                keyset_last_ts = raw_ts.isoformat()
            else:
                keyset_last_ts = str(raw_ts) if raw_ts else keyset_last_ts
            keyset_last_polymer = str(
                last_row_dict.get("polymer") or last_row_dict.get("id") or ""
            )

        count = len(rows)
        offset_counter += count
        cursor = _keyset_cursor_encode(since_iso, keyset_last_ts or "", keyset_last_polymer or "")

        # Serialise + measure payload size
        serial_t0 = time.perf_counter_ns()
        batch_payload = SyncBatchEvent(
            cursor=cursor,
            total=total,
            offset=offset_counter - count + legacy_start_offset,
            count=len(active_rows),
            materials=[m.model_dump() for m in materials],
        ).model_dump()
        sse_frame = _sse_data(batch_payload)
        serial_ms = (time.perf_counter_ns() - serial_t0) / 1_000_000.0
        _warn_slow(f"serialise@{offset_counter}", serial_ms, request_id)

        metrics.log_batch(
            offset_from=offset_counter - count,
            offset_to=offset_counter,
            active=len(active_rows),
            deleted=len(batch_deleted),
            payload_bytes=len(sse_frame.encode()),
        )

        # Log time-to-first-byte on the first batch
        if not first_byte_sent:
            ttfb_ms = (time.perf_counter_ns() - stream_start_ns) / 1_000_000.0
            logger.info(
                "stream_sync | event=first_byte | requestId=%s | ttfb_ms=%.1f",
                request_id, ttfb_ms,
            )
            _warn_slow("time_to_first_byte", ttfb_ms, request_id)
            first_byte_sent = True

        yield sse_frame

        # If we got fewer rows than the batch size, we've reached the end
        if count < batch_size:
            has_more = False
            break

        # Yield event loop between batches — prevents blocking the async worker
        await asyncio.sleep(INTER_BATCH_SLEEP_S)

    # ── Step 3: complete frame ────────────────────────────────────────────
    metrics.log_complete()
    total_elapsed_ms = (time.perf_counter_ns() - stream_start_ns) / 1_000_000.0
    logger.info(
        "stream_sync | event=stream_done | requestId=%s | "
        "total_sent=%d | deleted=%d | batches=%d | total_elapsed_ms=%.1f",
        request_id,
        metrics.total_sent,
        len(deleted_ids),
        metrics.batch_count,
        total_elapsed_ms,
    )

    yield _sse_data(
        SyncCompleteEvent(
            server_timestamp=now.isoformat(),
            total_sent=metrics.total_sent,
            inserted=metrics.total_sent,  # client determines insert vs update locally
            updated=0,
            deleted_ids=deleted_ids,
        ).model_dump()
    )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get(
    "/stream",
    summary="Stream incremental material sync via SSE",
    description=(
        "Streams all materials whose `updated_at` is after `since` as "
        "Server-Sent Events.  Use `cursor` to resume after a disconnect. "
        "On first sync omit `since` (or pass the Unix epoch) to receive "
        "the full catalog in batches."
    ),
    response_class=StreamingResponse,
)
async def stream_sync_materials(
    request: Request,
    since: str = Query(
        default="1970-01-01T00:00:00Z",
        description=(
            "ISO-8601 UTC timestamp.  Only materials whose `updated_at` is "
            "strictly after this value are returned.  Omit on first sync."
        ),
    ),
    batch_size: int = Query(
        default=DEFAULT_BATCH_SIZE,
        ge=MIN_BATCH_SIZE,
        le=MAX_BATCH_SIZE,
        description="Number of records per SSE batch (10–500, default 150).",
    ),
    cursor: str | None = Query(
        default=None,
        description=(
            "Resume token from the last received `batch` event.  "
            "Null on first attempt; set to the last cursor on reconnect."
        ),
    ),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """SSE streaming endpoint for offline-first material synchronization.

    Protocol
    --------
    1. Client sends GET /api/v1/materials/stream?since=<ts>[&cursor=<token>]
    2. Server streams ``data: {...}\\n\\n`` frames:
       - ``{"event": "batch", "cursor": "...", "total": N, "offset": X,
            "count": Y, "materials": [...]}``
       - (repeated for each batch)
       - ``{"event": "complete", "server_timestamp": "...",
            "total_sent": N, "deleted_ids": [...]}``
    3. On disconnect, client reconnects with last received ``cursor``.
    4. On ``complete``, client advances its local sync timestamp to
       ``server_timestamp``.

    Pagination
    ----------
    Uses keyset (cursor) pagination instead of LIMIT/OFFSET.  Each batch query
    is an O(log N) index seek rather than an O(N) full scan, making the 1000th
    batch just as fast as the 1st.  Required index::

        CREATE INDEX IF NOT EXISTS idx_fp_updated_at_polymer
            ON filtered_polymers (updated_at ASC, polymer ASC);

    The endpoint rejects invalid ``since`` values with HTTP 422 before
    opening the stream so the client knows immediately if the request is
    malformed.
    """
    request_id = getattr(request.state, "request_id", None) or \
        request.headers.get("X-Request-ID", "unknown")

    req_received_ns = time.perf_counter_ns()

    # Validate `since` before opening the stream
    try:
        datetime.fromisoformat(since.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid `since` timestamp format. Expected ISO-8601 UTC.",
        )

    # Resolve resume position from cursor
    resume_last_ts: str | None = None
    resume_last_polymer: str | None = None
    legacy_start_offset: int = 0

    if cursor:
        try:
            cur_since, last_ts, last_poly, leg_offset = _keyset_cursor_decode(cursor)
            # Use the since from the cursor to ensure consistency across reconnects
            since = cur_since
            if last_ts is not None and last_poly is not None:
                # v2 keyset cursor
                resume_last_ts = last_ts
                resume_last_polymer = last_poly
                logger.info(
                    "stream_sync | RESUME_KEYSET | requestId=%s | cursor_since=%s "
                    "| last_ts=%s | last_poly=%s",
                    request_id, cur_since, last_ts, last_poly,
                )
            else:
                # v1 legacy LIMIT/OFFSET cursor
                legacy_start_offset = max(0, leg_offset)
                logger.info(
                    "stream_sync | RESUME_LEGACY | requestId=%s | cursor_since=%s "
                    "| offset=%d",
                    request_id, cur_since, legacy_start_offset,
                )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid cursor: {exc}",
            )

    logger.info(
        "stream_sync | REQUEST | requestId=%s | since=%s | batch_size=%d | "
        "has_cursor=%s | client=%s | req_received_ms=%.1f",
        request_id, since, batch_size,
        cursor is not None,
        request.client.host if request.client else "unknown",
        (time.perf_counter_ns() - req_received_ns) / 1_000_000.0,
    )

    return StreamingResponse(
        _stream_sync(
            db=db,
            since_iso=since,
            batch_size=batch_size,
            request_id=request_id,
            resume_last_ts=resume_last_ts,
            resume_last_polymer=resume_last_polymer,
            legacy_start_offset=legacy_start_offset,
        ),
        media_type="text/event-stream",
        headers={
            # Prevent any intermediate proxy/CDN from buffering the stream.
            # nginx: X-Accel-Buffering: no disables proxy_buffering for this response.
            # All proxies: Cache-Control: no-cache tells them not to store the response.
            # These headers are NOT overwritten by SecurityHeadersMiddleware (which
            # skips Cache-Control for SSE responses — see main.py).
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
            "X-Request-ID": request_id,
        },
    )
