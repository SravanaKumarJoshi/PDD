"""Rate limiting middleware and sliding-window / token-bucket rate limiter."""

import time
import logging
from typing import Dict, Tuple
from fastapi import Request, HTTPException, status
from shared.ml.config import APP_CONFIG

logger = logging.getLogger(__name__)

RATE_LIMIT_CONFIG = APP_CONFIG.get("rate_limiting", {
    "enabled": True,
    "anonymous_limit": "10/minute",
    "user_limit": "60/minute",
    "admin_limit": "300/minute",
})

class RateLimiter:
    """In-memory sliding window rate limiter."""

    def __init__(self):
        # Client IP/Token -> List of timestamps
        self.requests: Dict[str, list] = {}

    def parse_limit(self, limit_str: str) -> Tuple[int, int]:
        """Parse limit string like '60/minute' into (max_requests, window_seconds)."""
        try:
            parts = limit_str.split("/")
            max_reqs = int(parts[0])
            unit = parts[1].lower()
            if "sec" in unit:
                window = 1
            elif "min" in unit:
                window = 60
            elif "hour" in unit:
                window = 3600
            else:
                window = 60
            return max_reqs, window
        except Exception:
            return 60, 60

    def is_allowed(self, client_id: str, role: str = "user") -> Tuple[bool, int, int]:
        """Check if request is allowed under rate limits."""
        if not RATE_LIMIT_CONFIG.get("enabled", True):
            return True, 100, 0

        limit_str = RATE_LIMIT_CONFIG.get(f"{role}_limit", RATE_LIMIT_CONFIG.get("user_limit", "60/minute"))
        max_reqs, window_seconds = self.parse_limit(limit_str)

        now = time.time()
        timestamps = self.requests.get(client_id, [])

        # Filter out timestamps outside window
        cutoff = now - window_seconds
        timestamps = [ts for ts in timestamps if ts > cutoff]

        if len(timestamps) >= max_reqs:
            oldest = timestamps[0]
            retry_after = int(window_seconds - (now - oldest)) + 1
            self.requests[client_id] = timestamps
            return False, 0, retry_after

        timestamps.append(now)
        self.requests[client_id] = timestamps
        remaining = max_reqs - len(timestamps)
        return True, remaining, 0

limiter = RateLimiter()
