"""Cache provider factory."""

from shared.ml.config import APP_CONFIG
from app.core.cache.base import BaseCacheProvider
from app.core.cache.memory import InMemoryCacheProvider
from app.core.cache.redis import RedisCacheProvider

class CacheProviderFactory:
    _instance: BaseCacheProvider = None

    @classmethod
    def get_cache_provider(cls) -> BaseCacheProvider:
        if cls._instance is None:
            cache_cfg = APP_CONFIG.get("cache", {})
            provider_name = (cache_cfg.get("provider") or "memory").lower()
            if provider_name == "redis":
                redis_url = cache_cfg.get("redis_url", "redis://localhost:6379/0")
                cls._instance = RedisCacheProvider(redis_url)
            else:
                cls._instance = InMemoryCacheProvider()
        return cls._instance
