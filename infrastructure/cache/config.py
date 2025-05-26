from fastapi import FastAPI
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache
from redis import asyncio as aioredis
import logging

from infrastructure.config.settings import settings

logger = logging.getLogger("heijunka_api.cache")

async def setup_cache(app: FastAPI) -> None:
    """
    Setup cache for the application.

    Tries to use Redis if available, falls back to in-memory cache if Redis is not available.

    Args:
        app: The FastAPI application
    """
    try:
        # Try to connect to Redis
        redis = aioredis.from_url(
            settings.redis_url, 
            encoding="utf8", 
            decode_responses=True
        )

        # Test the connection
        await redis.ping()

        # Store Redis client in app.state for shutdown cleanup
        app.state.redis_cache = redis

        # Initialize cache with Redis backend
        FastAPICache.init(
            RedisBackend(redis), 
            prefix="heijunka-cache:",
            expire=settings.cache_ttl_seconds
        )
        logger.info("Cache initialized with Redis backend")
    except Exception as e:
        # If Redis is not available, use in-memory cache
        logger.warning(f"Redis not available, using in-memory cache: {str(e)}")
        FastAPICache.init(
            InMemoryBackend(),
            prefix="heijunka-cache:",
            expire=settings.cache_ttl_seconds
        )
