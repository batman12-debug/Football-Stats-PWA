"""Per-IP rate limiting via Upstash Redis with in-memory fallback."""

import logging
import re
import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings
from app.services.cache import get_redis_client, redis_configured

logger = logging.getLogger(__name__)

RATE_LIMIT = 60
WRITE_RATE_LIMIT = 10
WINDOW_SECONDS = 60
EXEMPT_PATHS = {"/health"}

_IP_PATTERN = re.compile(r"^[\d.:a-fA-F]+$")

# In-memory fallback: ip -> (count, window_start_monotonic)
_memory_counters: dict[str, tuple[int, float]] = defaultdict(lambda: (0, 0.0))


def _sanitize_ip(raw: str) -> str:
    cleaned = raw.strip()[:45]
    if _IP_PATTERN.match(cleaned):
        return cleaned
    return "unknown"


def get_client_ip(request: Request) -> str:
    """Resolve client IP; only trust forwarded headers behind a known proxy."""
    if settings.trust_proxy_headers:
        cf_ip = request.headers.get("CF-Connecting-IP")
        if cf_ip:
            return _sanitize_ip(cf_ip.split(",")[0])

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return _sanitize_ip(real_ip.split(",")[0])

        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return _sanitize_ip(forwarded.split(",")[0])

    if request.client:
        return _sanitize_ip(request.client.host)
    return "unknown"


def _memory_rate_limit(key: str, limit: int) -> tuple[bool, int]:
    now = time.monotonic()
    count, window_start = _memory_counters[key]

    if now - window_start >= WINDOW_SECONDS:
        _memory_counters[key] = (1, now)
        return True, 0

    count += 1
    _memory_counters[key] = (count, window_start)
    retry_after = max(int(WINDOW_SECONDS - (now - window_start)), 1)

    if count > limit:
        return False, retry_after
    return True, 0


async def check_rate_limit(key: str, *, limit: int) -> tuple[bool, int]:
    """
    Return (allowed, retry_after_seconds).
    Uses Redis when available; falls back to in-memory counters.
    """
    if redis_configured():
        client = get_redis_client()
        redis_key = f"goalmind:rl:{key}"

        try:
            incr_response = await client.post("/", json=["INCR", redis_key])
            incr_response.raise_for_status()
            count = int(incr_response.json()["result"])

            if count == 1:
                await client.post("/", json=["EXPIRE", redis_key, WINDOW_SECONDS])

            ttl_response = await client.post("/", json=["TTL", redis_key])
            ttl_response.raise_for_status()
            ttl = int(ttl_response.json()["result"])
            retry_after = max(ttl, 1)

            if count > limit:
                return False, retry_after
            return True, 0
        except Exception:
            logger.exception("Rate limit Redis check failed for key=%s", key)
            if settings.rate_limit_fail_closed:
                return False, WINDOW_SECONDS

    return _memory_rate_limit(key, limit)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Limit each IP to 60 read requests/min; 10 write requests/min."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method == "OPTIONS" or request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        ip = get_client_ip(request)
        is_write = request.method in {"POST", "PUT", "PATCH", "DELETE"}
        limit = WRITE_RATE_LIMIT if is_write else RATE_LIMIT
        scope = "write" if is_write else "read"
        allowed, retry_after = await check_rate_limit(f"{scope}:{ip}", limit=limit)

        if not allowed:
            logger.warning(
                "Rate limit exceeded for ip=%s path=%s method=%s",
                ip,
                request.url.path,
                request.method,
            )
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)
