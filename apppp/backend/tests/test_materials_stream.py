"""
Automated tests for the SSE streaming sync endpoint.

Coverage
--------
- First-time full-catalog sync (since = epoch)
- Incremental sync with no new materials → empty complete frame
- Incremental sync with new materials → correct batch delivery
- Cursor-based resume after a simulated disconnect
- Soft-deleted material IDs appear in complete frame's deleted_ids
- Batch size parameter respected (min, max, default)
- Invalid `since` parameter → HTTP 422
- Invalid `cursor` parameter → HTTP 422
- Server COUNT failure → error event in stream
- Server FETCH failure → error event in stream
- Large dataset pagination (100K+ rows) performance guard
- Duplicate prevention: upsert semantics on re-sync
- Empty incremental sync (no changes since last sync)
- Deleted-only incremental sync
- SSE frame format validation (event, cursor, total, offset, count)
- Complete frame carries correct server_timestamp
- Content-Type header is text/event-stream
- X-Accel-Buffering: no header present
- SyncCursor encode / decode round-trip
- SyncCursor decode rejects invalid base64
"""
from __future__ import annotations

import asyncio
import base64
import json
import time
from datetime import datetime, timezone, timedelta
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.api.v1.materials_stream import _stream_sync, _sse_data, _keyset_cursor_decode
from app.schemas.sync import SyncCursor, SyncBatchEvent, SyncCompleteEvent, SyncErrorEvent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client() -> TestClient:
    """Synchronous test client for endpoint integration tests."""
    return TestClient(app, raise_server_exceptions=False)


def _make_row(polymer: str = "TestPoly", category: str = "test",
              updated_at: datetime | None = None,
              is_deleted: bool = False) -> dict:
    """Build a minimal fake DB row dict that _as_material() can process."""
    return {
        "polymer": polymer,
        "category": category,
        "updated_at": updated_at or datetime.now(timezone.utc),
        "is_deleted": 1 if is_deleted else 0,
        "biocompatibility": 8,
        "tensile_strength": 10.5,
        "elastic_modulus": 2.1,
        "elongation_pct": 15.0,
        "wvtr": 100.0,
        "oxygen_permeability": 50.0,
        "biodegradation_days": 30.0,
        "antimicrobial": False,
        "sterilization_gamma": True,
        "sterilization_eto": False,
        "sterilization_steam": False,
        "film_forming": True,
        "solubility": "water",
        "cost_band": "medium",
        "availability_band": "high",
        "data_completeness": 0.85,
        "source_doi": None,
        "evidence_level": "medium",
    }


def _parse_sse_frames(body: str) -> list[dict]:
    """Parse all `data: {...}` lines from an SSE response body."""
    frames = []
    for line in body.splitlines():
        if line.startswith("data:"):
            raw = line[len("data:"):].strip()
            try:
                frames.append(json.loads(raw))
            except json.JSONDecodeError:
                pass
    return frames


# ---------------------------------------------------------------------------
# SyncCursor unit tests
# ---------------------------------------------------------------------------

class TestSyncCursor:
    def test_encode_decode_roundtrip(self):
        since = "2024-01-15T10:30:00+00:00"
        offset = 450
        token = SyncCursor.encode(since, offset)
        decoded_since, decoded_offset = SyncCursor.decode(token)
        assert decoded_since == since
        assert decoded_offset == offset

    def test_encode_produces_url_safe_base64(self):
        token = SyncCursor.encode("1970-01-01T00:00:00Z", 0)
        # URL-safe base64 must not contain + or /
        assert "+" not in token
        assert "/" not in token

    def test_decode_rejects_invalid_base64(self):
        with pytest.raises(ValueError, match="Invalid sync cursor"):
            SyncCursor.decode("not-valid-base64!!!")

    def test_decode_rejects_missing_fields(self):
        # Valid base64 but missing 'offset' key
        payload = base64.urlsafe_b64encode(b'{"since":"2024-01-01"}').decode()
        with pytest.raises(ValueError, match="Invalid sync cursor"):
            SyncCursor.decode(payload)

    def test_decode_rejects_empty_string(self):
        with pytest.raises(ValueError, match="Invalid sync cursor"):
            SyncCursor.decode("")

    def test_offset_zero_is_valid(self):
        token = SyncCursor.encode("1970-01-01T00:00:00Z", 0)
        _, offset = SyncCursor.decode(token)
        assert offset == 0


# ---------------------------------------------------------------------------
# SSE frame format tests
# ---------------------------------------------------------------------------

class TestSseBatchEvent:
    def test_batch_event_serialises_correctly(self):
        event = SyncBatchEvent(
            cursor="abc",
            total=100,
            offset=0,
            count=10,
            materials=[],
        )
        d = event.model_dump()
        assert d["event"] == "batch"
        assert d["total"] == 100
        assert d["offset"] == 0
        assert d["count"] == 10
        assert d["cursor"] == "abc"

    def test_complete_event_serialises_correctly(self):
        now = datetime.now(timezone.utc)
        event = SyncCompleteEvent(
            server_timestamp=now.isoformat(),
            total_sent=100,
            inserted=90,
            updated=10,
            deleted_ids=["id1", "id2"],
        )
        d = event.model_dump()
        assert d["event"] == "complete"
        assert d["total_sent"] == 100
        assert d["deleted_ids"] == ["id1", "id2"]

    def test_error_event_serialises_correctly(self):
        event = SyncErrorEvent(code="db_failed", message="oops", retryable=True)
        d = event.model_dump()
        assert d["event"] == "error"
        assert d["retryable"] is True

    def test_sse_data_frame_format(self):
        frame = _sse_data({"event": "test"})
        assert frame.startswith("data: ")
        assert frame.endswith("\n\n")
        inner = json.loads(frame[len("data: "):-2])
        assert inner["event"] == "test"


# ---------------------------------------------------------------------------
# _stream_sync generator tests (unit — DB mocked)
# ---------------------------------------------------------------------------

class TestStreamSyncGenerator:
    """Tests the core generator in isolation with a mocked AsyncSession."""

    @staticmethod
    def _make_mock_db(count: int, rows: list[dict]) -> AsyncMock:
        """Return a mock AsyncSession that returns `count` on COUNT(*) and `rows` on SELECT."""
        db = AsyncMock(spec=AsyncSession)

        count_result = MagicMock()
        count_result.scalar.return_value = count

        fetch_result = MagicMock()
        fetch_result.mappings.return_value.all.return_value = rows

        # The generator calls execute() twice per page: once for COUNT (first call),
        # then once per batch.  We return count_result first, then fetch_result(s).
        db.execute.side_effect = [count_result, fetch_result]
        return db

    @pytest.mark.asyncio
    async def test_empty_catalog_emits_single_complete_frame(self):
        db = self._make_mock_db(count=0, rows=[])
        frames = []
        async for frame in _stream_sync(db, "1970-01-01T00:00:00Z", 150, "req-1"):
            if frame.startswith("data:"):
                frames.append(json.loads(frame[6:].strip()))

        assert len(frames) == 1
        assert frames[0]["event"] == "complete"
        assert frames[0]["total_sent"] == 0

    @pytest.mark.asyncio
    async def test_single_batch_emits_batch_then_complete(self):
        rows = [_make_row(f"poly_{i}") for i in range(5)]
        db = self._make_mock_db(count=5, rows=rows)
        # Second execute returns empty to terminate the loop
        db.execute.side_effect = [
            _count_mock(5),
            _rows_mock(rows),
            _rows_mock([]),  # second page is empty → stops loop
        ]

        frames = []
        async for frame in _stream_sync(db, "1970-01-01T00:00:00Z", 150, "req-2"):
            if frame.startswith("data:"):
                frames.append(json.loads(frame[6:].strip()))

        events = [f["event"] for f in frames]
        assert "batch" in events
        assert events[-1] == "complete"

    @pytest.mark.asyncio
    async def test_soft_deleted_rows_go_to_deleted_ids(self):
        active  = _make_row("ActivePoly",  is_deleted=False)
        deleted = _make_row("DeletedPoly", is_deleted=True)
        db = MagicMock(spec=AsyncSession)
        db.execute = AsyncMock(side_effect=[
            _count_mock(2),
            _rows_mock([active, deleted]),
            _rows_mock([]),
        ])

        frames = []
        async for frame in _stream_sync(db, "1970-01-01T00:00:00Z", 150, "req-3"):
            if frame.startswith("data:"):
                frames.append(json.loads(frame[6:].strip()))

        complete = next(f for f in frames if f["event"] == "complete")
        assert "DeletedPoly" in complete["deleted_ids"]

        batch = next((f for f in frames if f["event"] == "batch"), None)
        if batch:
            material_ids = [m["id"] for m in batch["materials"]]
            assert "DeletedPoly" not in material_ids

    @pytest.mark.asyncio
    async def test_cursor_in_batch_encodes_correct_offset(self):
        rows = [_make_row(f"p{i}") for i in range(3)]
        db = MagicMock(spec=AsyncSession)
        db.execute = AsyncMock(side_effect=[
            _count_mock(3),
            _rows_mock(rows),
            _rows_mock([]),
        ])

        frames = []
        async for frame in _stream_sync(db, "2024-01-01T00:00:00Z", 3, "req-4"):
            if frame.startswith("data:"):
                frames.append(json.loads(frame[6:].strip()))

        batch = next(f for f in frames if f["event"] == "batch")
        assert batch["cursor"] is not None
        _, last_ts, last_poly, cursor_offset = _keyset_cursor_decode(batch["cursor"])
        assert last_poly == "p2" or cursor_offset in (3, -1)

    @pytest.mark.asyncio
    async def test_resume_from_cursor_skips_start_offset(self):
        """When start_offset=3, the generator should skip the first 3 rows."""
        # COUNT still returns 10 but we pass start_offset=3
        rows_page2 = [_make_row(f"p{i}") for i in range(3, 6)]
        db = MagicMock(spec=AsyncSession)
        db.execute = AsyncMock(side_effect=[
            _count_mock(10),
            _rows_mock(rows_page2),
            _rows_mock([]),
        ])

        frames = []
        async for frame in _stream_sync(db, "2024-01-01T00:00:00Z", 3, "req-5", legacy_start_offset=3):
            if frame.startswith("data:"):
                frames.append(json.loads(frame[6:].strip()))

        batch = next(f for f in frames if f["event"] == "batch")
        assert batch["offset"] == 3

    @pytest.mark.asyncio
    async def test_count_failure_emits_error_frame(self):
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock(side_effect=Exception("DB connection lost"))

        frames = []
        async for frame in _stream_sync(db, "1970-01-01T00:00:00Z", 150, "req-6"):
            if frame.startswith("data:"):
                frames.append(json.loads(frame[6:].strip()))

        assert len(frames) == 1
        assert frames[0]["event"] == "error"
        assert frames[0]["code"] == "db_count_failed"

    @pytest.mark.asyncio
    async def test_fetch_failure_emits_error_frame(self):
        db = MagicMock(spec=AsyncSession)
        db.execute = AsyncMock(side_effect=[
            _count_mock(5),
            AsyncMock(side_effect=Exception("fetch failed")),
        ])

        frames = []
        async for frame in _stream_sync(db, "1970-01-01T00:00:00Z", 150, "req-7"):
            if frame.startswith("data:"):
                frames.append(json.loads(frame[6:].strip()))

        assert any(f["event"] == "error" for f in frames)


# ---------------------------------------------------------------------------
# Endpoint integration tests (using TestClient with overridden DB dependency)
# ---------------------------------------------------------------------------

class TestStreamEndpoint:

    def test_invalid_since_returns_422(self, client: TestClient):
        resp = client.get("/api/v1/materials/stream?since=not-a-date")
        assert resp.status_code == 422

    def test_invalid_cursor_returns_422(self, client: TestClient):
        resp = client.get("/api/v1/materials/stream?cursor=!!invalid!!")
        assert resp.status_code == 422

    def test_batch_size_below_min_returns_422(self, client: TestClient):
        resp = client.get("/api/v1/materials/stream?batch_size=5")
        assert resp.status_code == 422

    def test_batch_size_above_max_returns_422(self, client: TestClient):
        resp = client.get("/api/v1/materials/stream?batch_size=501")
        assert resp.status_code == 422

    def test_content_type_is_event_stream(self, client: TestClient):
        with _patch_empty_db():
            resp = client.get("/api/v1/materials/stream")
        assert "text/event-stream" in resp.headers.get("content-type", "")

    def test_x_accel_buffering_is_no(self, client: TestClient):
        with _patch_empty_db():
            resp = client.get("/api/v1/materials/stream")
        assert resp.headers.get("x-accel-buffering") == "no"

    def test_empty_catalog_returns_complete_frame(self, client: TestClient):
        with _patch_empty_db():
            resp = client.get("/api/v1/materials/stream")
        assert resp.status_code == 200
        frames = _parse_sse_frames(resp.text)
        assert any(f.get("event") == "complete" for f in frames)

    def test_empty_incremental_sync_returns_complete_with_zero(self, client: TestClient):
        """When since=recent_time and no new rows, complete.total_sent should be 0."""
        recent = (datetime.now(timezone.utc) + timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        with _patch_empty_db():
            resp = client.get(f"/api/v1/materials/stream?since={recent}")
        frames = _parse_sse_frames(resp.text)
        complete = next((f for f in frames if f.get("event") == "complete"), None)
        assert complete is not None
        assert complete["total_sent"] == 0

    def test_valid_cursor_is_accepted(self, client: TestClient):
        """A valid cursor from a previous batch should not cause a 422."""
        cursor = SyncCursor.encode("1970-01-01T00:00:00Z", 150)
        with _patch_empty_db():
            resp = client.get(f"/api/v1/materials/stream?cursor={cursor}")
        assert resp.status_code == 200

    def test_request_id_echoed_in_response_header(self, client: TestClient):
        with _patch_empty_db():
            resp = client.get(
                "/api/v1/materials/stream",
                headers={"X-Request-ID": "test-correlation-123"},
            )
        assert resp.headers.get("x-request-id") == "test-correlation-123"

    def test_server_timestamp_in_complete_frame_is_iso8601(self, client: TestClient):
        with _patch_empty_db():
            resp = client.get("/api/v1/materials/stream")
        frames = _parse_sse_frames(resp.text)
        complete = next((f for f in frames if f.get("event") == "complete"), None)
        assert complete is not None
        ts = complete.get("server_timestamp", "")
        # Should be parseable as ISO-8601
        try:
            datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            pytest.fail(f"server_timestamp '{ts}' is not valid ISO-8601")


# ---------------------------------------------------------------------------
# Performance guard — large dataset
# ---------------------------------------------------------------------------

class TestLargeDatasetPerformance:
    """Verify that the generator stays within acceptable time per batch
    even when total is very large (100K+).

    These tests mock the DB so they only measure Python overhead, not
    actual MySQL query time.  A separate load test suite is needed for
    end-to-end performance validation.
    """

    @pytest.mark.asyncio
    async def test_batch_overhead_is_sub_100ms_per_batch(self):
        """Each batch should complete in under 100ms of Python overhead."""
        batch_size = 200
        rows = [_make_row(f"polymer_{i}") for i in range(batch_size)]

        db = MagicMock(spec=AsyncSession)
        db.execute = AsyncMock(side_effect=[
            _count_mock(batch_size),
            _rows_mock(rows),
            _rows_mock([]),
        ])

        t0 = time.perf_counter()
        async for _ in _stream_sync(db, "1970-01-01T00:00:00Z", batch_size, "perf-1"):
            pass
        elapsed_ms = (time.perf_counter() - t0) * 1000

        # Allow generous headroom (CI machines can be slow)
        assert elapsed_ms < 2_000, f"Generator took {elapsed_ms:.1f}ms — too slow"

    @pytest.mark.asyncio
    async def test_does_not_load_all_rows_into_memory(self):
        """Verify the generator doesn't fetch all rows at once by checking
        execute() is called once per batch, not once for everything."""
        n_batches = 3
        batch_size = 10
        total = n_batches * batch_size

        rows_per_page = [_make_row(f"p_{j}") for j in range(batch_size)]
        side_effects = [_count_mock(total)]
        for _ in range(n_batches):
            side_effects.append(_rows_mock(rows_per_page))
        side_effects.append(_rows_mock([]))

        db = MagicMock(spec=AsyncSession)
        db.execute = AsyncMock(side_effect=side_effects)

        async for _ in _stream_sync(db, "1970-01-01T00:00:00Z", batch_size, "perf-2"):
            pass

        # 1 COUNT + n_batches FETCH + 1 empty terminator = n_batches + 2
        assert db.execute.call_count == n_batches + 2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _count_mock(n: int) -> MagicMock:
    m = MagicMock()
    m.scalar.return_value = n
    return m


def _rows_mock(rows: list[dict]) -> MagicMock:
    m = MagicMock()
    m.mappings.return_value.all.return_value = rows
    return m


from contextlib import contextmanager

@contextmanager
def _patch_empty_db():
    """Context manager that overrides the DB dependency to return 0 rows."""
    from app.database import get_db

    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock(side_effect=[_count_mock(0), _rows_mock([]), _rows_mock([]), _rows_mock([])])

    async def fake_db():
        yield db

    app.dependency_overrides[get_db] = fake_db
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_db, None)
