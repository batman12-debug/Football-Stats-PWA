"""Upstash Redis cache layer via REST API."""

import json
import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_redis_client: httpx.AsyncClient | None = None


def get_redis_client() -> httpx.AsyncClient:
    global _redis_client
    if _redis_client is None:
        _redis_client = httpx.AsyncClient(
            base_url=settings.upstash_redis_url,
            headers={"Authorization": f"Bearer {settings.upstash_redis_token}"},
            timeout=httpx.Timeout(3.0, connect=2.0),
        )
    return _redis_client


def redis_configured() -> bool:
    return settings.redis_configured


async def get_cached(key: str) -> str | None:
    """Retrieve a string value from cache."""
    if not redis_configured():
        return None

    try:
        client = get_redis_client()
        response = await client.get(f"/get/{key}")
        if response.status_code != 200:
            return None

        result = response.json().get("result")
        return result if isinstance(result, str) else None
    except httpx.HTTPError:
        logger.warning("Redis unavailable — cache read skipped for key=%s", key)
        return None


async def set_cached(key: str, value: str, ttl_seconds: int = 3600) -> None:
    """Store a string value in cache with TTL."""
    if not redis_configured():
        return

    try:
        client = get_redis_client()
        await client.post("/", json=["SET", key, value, "EX", ttl_seconds])
    except httpx.HTTPError:
        logger.warning("Redis unavailable — cache write skipped for key=%s", key)


async def delete_cached(key: str) -> None:
    """Remove a value from cache."""
    if not redis_configured():
        return

    try:
        client = get_redis_client()
        await client.post("/", json=["DEL", key])
    except httpx.HTTPError:
        logger.warning("Redis unavailable — cache delete skipped for key=%s", key)


async def get_json_cached(key: str) -> Any | None:
    """Retrieve and deserialize a JSON value from cache."""
    raw = await get_cached(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


async def set_json_cached(key: str, value: Any, ttl_seconds: int = 3600) -> None:
    """Serialize and store a JSON value in cache with TTL."""
    await set_cached(key, json.dumps(value), ttl_seconds=ttl_seconds)
