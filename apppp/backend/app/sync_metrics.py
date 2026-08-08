"""Structured sync metrics and logging helpers.

All sync-related log lines follow a consistent key=value format so they can
be parsed and aggregated by log management tools (CloudWatch Insights,
Datadog, Loki, Papertrail, etc.) without custom parsers.

Example log output
------------------
INFO  materials.sync | event=start | requestId=abc123 | since=2024-01-01T00:00:00Z
      | total=1200 | batch_size=150 | client=10.0.2.2
INFO  materials.sync | event=count | requestId=abc123 | total=1200 | count_ms=12.4
INFO  materials.sync | event=first_byte | requestId=abc123 | ttfb_ms=48.3
INFO  materials.sync | event=batch | requestId=abc123 | batch=1 | offset=0→150
      | active=148 | deleted=2 | batch_ms=42.1 | payload_bytes=38400 | rps=3523.4
INFO  materials.sync | event=batch | requestId=abc123 | batch=2 | offset=150→300
      | active=150 | deleted=0 | batch_ms=38.7 | payload_bytes=38900 | rps=3875.9
INFO  materials.sync | event=complete | requestId=abc123 | total_sent=1198
      | deleted=2 | batches=8 | elapsed_ms=412.3 | avg_rps=2905.6
WARN  materials.sync | event=slow_batch | requestId=abc123 | batch=3
      | batch_ms=523.4  ⚠ SLOW (>500ms)
ERROR materials.sync | event=error | requestId=abc123 | code=db_fetch_failed
      | offset=300 | error=... | retryable=true
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger("materials.sync")

#: Any operation (query, serialisation) slower than this is logged at WARNING.
#: Set to 500 ms as required by the performance spec.
SLOW_BATCH_THRESHOLD_MS: float = 500.0

#: Streams longer than this emit a summary warning
SLOW_STREAM_THRESHOLD_MS: float = 30_000.0


@dataclass
class SyncMetrics:
    """Accumulates counters for a single streaming sync request.

    Create one instance per request and call the record methods as each
    phase completes.  Call ``log_complete()`` at the end to emit the final
    structured summary line including average records-per-second.
    """

    request_id: str
    since_iso: str
    batch_size: int
    client_host: str = "unknown"

    # Counters updated as batches are streamed
    total_matched: int = 0
    total_sent: int = 0
    total_deleted: int = 0
    batch_count: int = 0
    error_count: int = 0

    # Timing
    _start_ns: int = field(default_factory=lambda: time.perf_counter_ns(), init=False)
    _batch_start_ns: int = field(default_factory=lambda: time.perf_counter_ns(), init=False)

    def elapsed_ms(self) -> float:
        return (time.perf_counter_ns() - self._start_ns) / 1_000_000.0

    def log_start(self) -> None:
        logger.info(
            "materials.sync | event=start | requestId=%s | since=%s | "
            "batch_size=%d | client=%s",
            self.request_id, self.since_iso, self.batch_size, self.client_host,
        )

    def log_total_known(self, total: int) -> None:
        self.total_matched = total
        logger.info(
            "materials.sync | event=count | requestId=%s | total=%d",
            self.request_id, total,
        )

    def log_empty(self) -> None:
        logger.info(
            "materials.sync | event=empty | requestId=%s | "
            "since=%s | elapsed_ms=%.1f",
            self.request_id, self.since_iso, self.elapsed_ms(),
        )

    def begin_batch(self) -> None:
        self._batch_start_ns = time.perf_counter_ns()

    def log_batch(
        self,
        offset_from: int,
        offset_to: int,
        active: int,
        deleted: int,
        payload_bytes: int,
    ) -> None:
        self.batch_count += 1
        self.total_sent += active
        self.total_deleted += deleted

        batch_ms = (time.perf_counter_ns() - self._batch_start_ns) / 1_000_000.0
        is_slow = batch_ms > SLOW_BATCH_THRESHOLD_MS

        # Records per second for this batch
        rps = (active / (batch_ms / 1000.0)) if batch_ms > 0 else 0.0

        log_level = logging.WARNING if is_slow else logging.INFO
        logger.log(
            log_level,
            "materials.sync | event=%s | requestId=%s | batch=%d | "
            "offset=%d→%d | active=%d | deleted=%d | "
            "batch_ms=%.1f | payload_bytes=%d | rps=%.1f%s",
            "slow_batch" if is_slow else "batch",
            self.request_id,
            self.batch_count,
            offset_from, offset_to,
            active, deleted,
            batch_ms, payload_bytes, rps,
            "  ⚠ SLOW (>500ms)" if is_slow else "",
        )

    def log_error(self, code: str, error: str, offset: int = -1) -> None:
        self.error_count += 1
        logger.error(
            "materials.sync | event=error | requestId=%s | code=%s | "
            "offset=%d | error=%s | retryable=true",
            self.request_id, code, offset, error,
        )

    def log_complete(self) -> None:
        elapsed = self.elapsed_ms()
        is_slow = elapsed > SLOW_STREAM_THRESHOLD_MS

        # Average records per second over the full stream
        avg_rps = (self.total_sent / (elapsed / 1000.0)) if elapsed > 0 else 0.0

        log_level = logging.WARNING if is_slow else logging.INFO
        logger.log(
            log_level,
            "materials.sync | event=complete | requestId=%s | "
            "total_matched=%d | total_sent=%d | deleted=%d | "
            "batches=%d | elapsed_ms=%.1f | avg_rps=%.1f | errors=%d%s",
            self.request_id,
            self.total_matched, self.total_sent, self.total_deleted,
            self.batch_count, elapsed, avg_rps, self.error_count,
            "  ⚠ SLOW STREAM" if is_slow else "",
        )


def make_request_id(request) -> str:  # type: ignore[no-untyped-def]
    """Extract or generate a correlation ID from a FastAPI Request."""
    return (
        getattr(request.state, "request_id", None)
        or request.headers.get("X-Request-ID", "")
        or f"srv-{int(time.perf_counter_ns())}"
    )


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()
