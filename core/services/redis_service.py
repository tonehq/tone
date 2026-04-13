import json
from typing import Optional, Any
from loguru import logger

import redis

_client: Optional[redis.Redis] = None


def init_redis(redis_url: str) -> None:
    """Initialize the Redis connection. Call once at app startup."""
    global _client
    try:
        _client = redis.from_url(redis_url, decode_responses=True)
        _client.ping()
        logger.info("Redis connected: {}", redis_url.split("@")[-1] if "@" in redis_url else redis_url)
    except Exception as e:
        logger.warning("Redis not available (caching disabled): {}", e)
        _client = None


def get_redis() -> Optional[redis.Redis]:
    """Get the Redis client instance. Returns None if Redis is not connected."""
    return _client


def cache_get(key: str) -> Optional[Any]:
    """Get a JSON value from cache. Returns None on miss or if Redis is unavailable."""
    if not _client:
        return None
    try:
        data = _client.get(key)
        if data is not None:
            return json.loads(data)
    except Exception as e:
        logger.debug("Redis cache_get error for key={}: {}", key, e)
    return None


def cache_set(key: str, value: Any, ttl_seconds: int = 1800) -> bool:
    """Set a JSON value in cache with TTL (default: 30 minutes). Returns True on success."""
    if not _client:
        return False
    try:
        _client.setex(key, ttl_seconds, json.dumps(value))
        return True
    except Exception as e:
        logger.debug("Redis cache_set error for key={}: {}", key, e)
        return False


def cache_delete(key: str) -> bool:
    """Delete a key from cache. Returns True on success."""
    if not _client:
        return False
    try:
        _client.delete(key)
        return True
    except Exception as e:
        logger.debug("Redis cache_delete error for key={}: {}", key, e)
        return False


def cache_delete_pattern(pattern: str) -> int:
    """Delete all keys matching a pattern (e.g., 'agent:*'). Returns count of deleted keys."""
    if not _client:
        return 0
    try:
        keys = _client.keys(pattern)
        if keys:
            return _client.delete(*keys)
    except Exception as e:
        logger.debug("Redis cache_delete_pattern error for pattern={}: {}", pattern, e)
    return 0
