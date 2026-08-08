"""Base cache provider abstract interface."""

from abc import ABC, abstractmethod
from typing import Any, Optional

class BaseCacheProvider(ABC):
    """Abstract interface for caching providers (In-Memory, Redis, Distributed)."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Retrieve value by key."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: int = 1800) -> None:
        """Store value with key and TTL."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all cache entries."""
        pass
