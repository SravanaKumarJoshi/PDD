"""In-memory cache provider implementation."""

import time
from typing import Any, Dict, Optional, Tuple
from app.core.cache.base import BaseCacheProvider

class InMemoryCacheProvider(BaseCacheProvider):
    def __init__(self):
        # Key -> (value, expiry_timestamp)
        self._store: Dict[str, Tuple[Any, float]] = {}

    async def get(self, key: str) -> Optional[Any]:
        if key not in self._store:
            return None
        val, expiry = self._store[key]
        if time.time() > expiry:
            del self._store[key]
            return None
        return val

    async def set(self, key: str, value: Any, ttl_seconds: int = 1800) -> None:
        expiry = time.time() + ttl_seconds
        self._store[key] = (value, expiry)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def clear(self) -> None:
        self._store.clear()
