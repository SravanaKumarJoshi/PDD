"""Redis cache provider implementation with graceful in-memory fallback."""

import json
import logging
from typing import Any, Optional
from app.core.cache.base import BaseCacheProvider
from app.core.cache.memory import InMemoryCacheProvider

logger = logging.getLogger(__name__)

class RedisCacheProvider(BaseCacheProvider):
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self.fallback = InMemoryCacheProvider()
        self.redis = None
        try:
            import redis.asyncio as aioredis
            self.redis = aioredis.from_url(redis_url, decode_responses=True)
        except Exception as e:
            logger.warning(f"Redis initialization failed ({e}). Using in-memory fallback.")

    async def get(self, key: str) -> Optional[Any]:
        if self.redis is None:
            return await self.fallback.get(key)
        try:
            val = await self.redis.get(key)
            return json.loads(val) if val else None
        except Exception as e:
            logger.warning(f"Redis get failed ({e}). Falling back to memory.")
            return await self.fallback.get(key)

    async def set(self, key: str, value: Any, ttl_seconds: int = 1800) -> None:
        if self.redis is None:
            await self.fallback.set(key, value, ttl_seconds)
            return
        try:
            payload = json.dumps(value, default=str)
            await self.redis.set(key, payload, ex=ttl_seconds)
        except Exception as e:
            logger.warning(f"Redis set failed ({e}). Falling back to memory.")
            await self.fallback.set(key, value, ttl_seconds)

    async def delete(self, key: str) -> None:
        if self.redis:
            try:
                await self.redis.delete(key)
            except Exception:
                pass
        await self.fallback.delete(key)

    async def clear(self) -> None:
        if self.redis:
            try:
                await self.redis.flushdb()
            except Exception:
                pass
        await self.fallback.clear()
