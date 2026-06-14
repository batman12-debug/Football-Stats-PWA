"""API-Football (api-sports.io) client — all external football data calls."""

import asyncio
import time
from collections import deque
from typing import Any

import httpx

from app.config import settings
from app.services.cache import get_json_cached, set_json_cached

CACHE_TTL_STATS = 3600
CACHE_TTL_FIXTURES = 300

WC_LEAGUE_ID = settings.wc_league_id
WC_SEASON = settings.wc_season


class APIFootballError(Exception):
    """Raised when API-Football requests fail."""


class RateLimiter:
    """Token-bucket rate limiter: max N requests per second."""

    def __init__(self, max_requests: int = 10, per_seconds: float = 1.0) -> None:
        self.max_requests = max_requests
        self.per_seconds = per_seconds
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            while self._timestamps and now - self._timestamps[0] >= self.per_seconds:
                self._timestamps.popleft()

            if len(self._timestamps) >= self.max_requests:
                sleep_for = self.per_seconds - (now - self._timestamps[0])
                if sleep_for > 0:
                    await asyncio.sleep(sleep_for)
                now = time.monotonic()
                while self._timestamps and now - self._timestamps[0] >= self.per_seconds:
                    self._timestamps.popleft()

            self._timestamps.append(time.monotonic())


class APIFootballClient:
    """Async HTTP client for API-Football with rate limiting and Redis caching."""

    def __init__(self) -> None:
        self._rate_limiter = RateLimiter(max_requests=10, per_seconds=1.0)
        self._client = httpx.AsyncClient(
            base_url=settings.api_football_base_url,
            headers={"x-apisports-key": settings.api_football_key},
            timeout=30.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    def _ensure_configured(self) -> None:
        if not settings.api_football_configured:
            raise APIFootballError(
                "API_FOOTBALL_KEY is not set. Copy backend/.env.example to backend/.env "
                "and add your key from https://dashboard.api-football.com/"
            )

    async def _request(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        self._ensure_configured()
        await self._rate_limiter.acquire()
        response = await self._client.get(endpoint, params=params or {})

        if response.status_code == 403:
            raise APIFootballError(
                "API-Football returned 403 Forbidden. Verify API_FOOTBALL_KEY in backend/.env "
                "and that your plan includes access to this endpoint."
            )

        response.raise_for_status()
        data = response.json()

        errors = data.get("errors")
        if errors:
            if isinstance(errors, dict) and errors.get("rateLimit"):
                raise APIFootballError(f"API-Football rate limit: {errors['rateLimit']}")
            raise APIFootballError(f"API-Football error: {errors}")

        return data.get("response", [])

    async def _cached_request(
        self,
        cache_key: str,
        endpoint: str,
        params: dict[str, Any],
        ttl_seconds: int,
    ) -> Any:
        cached = await get_json_cached(cache_key)
        if cached is not None:
            return cached

        result = await self._request(endpoint, params)
        await set_json_cached(cache_key, result, ttl_seconds=ttl_seconds)
        return result

    async def get_teams(self, league_id: int, season: int) -> list[dict]:
        """Fetch all teams for a league and season."""
        cache_key = f"af:teams:{league_id}:{season}"
        return await self._cached_request(
            cache_key,
            "/teams",
            {"league": league_id, "season": season},
            ttl_seconds=CACHE_TTL_STATS,
        )

    async def get_fixtures(self, league_id: int, season: int) -> list[dict]:
        """Fetch all fixtures for a league and season."""
        cache_key = f"af:fixtures:{league_id}:{season}"
        return await self._cached_request(
            cache_key,
            "/fixtures",
            {"league": league_id, "season": season},
            ttl_seconds=CACHE_TTL_FIXTURES,
        )

    async def get_h2h(self, team1_id: int, team2_id: int) -> list[dict]:
        """Fetch head-to-head fixtures between two teams."""
        h2h_key = f"{min(team1_id, team2_id)}-{max(team1_id, team2_id)}"
        cache_key = f"af:h2h:{h2h_key}"
        return await self._cached_request(
            cache_key,
            "/fixtures/headtohead",
            {"h2h": f"{team1_id}-{team2_id}"},
            ttl_seconds=CACHE_TTL_STATS,
        )

    async def get_team_statistics(
        self, team_id: int, league_id: int, season: int
    ) -> dict:
        """Fetch team statistics for a league and season."""
        cache_key = f"af:stats:{team_id}:{league_id}:{season}"
        cached = await get_json_cached(cache_key)
        if cached is not None:
            return cached

        result = await self._request(
            "/teams/statistics",
            {"team": team_id, "league": league_id, "season": season},
        )
        stats = result[0] if result else {}
        await set_json_cached(cache_key, stats, ttl_seconds=CACHE_TTL_STATS)
        return stats

    async def get_fixture(self, fixture_id: int) -> dict | None:
        """Fetch a single fixture by ID."""
        cache_key = f"af:fixture:{fixture_id}"
        cached = await get_json_cached(cache_key)
        if cached is not None:
            return cached

        result = await self._request("/fixtures", {"id": fixture_id})
        if not result:
            return None

        fixture = result[0]
        await set_json_cached(cache_key, fixture, ttl_seconds=CACHE_TTL_FIXTURES)
        return fixture

    async def get_live_fixtures(self, league_id: int, season: int) -> list[dict]:
        """Fetch currently live fixtures (not cached — polled on demand)."""
        return await self._request(
            "/fixtures",
            {"league": league_id, "season": season, "live": "all"},
        )

    async def get_fixture_statistics(self, fixture_id: int) -> list[dict]:
        """Fetch live or final per-team statistics for a fixture (not cached)."""
        return await self._request("/fixtures/statistics", {"fixture": fixture_id})

    async def get_team_statistics_batch(
        self, team_ids: list[int], league_id: int, season: int
    ) -> dict[int, dict]:
        """Fetch statistics for multiple teams, respecting rate limits."""
        results: dict[int, dict] = {}
        for team_id in team_ids:
            results[team_id] = await self.get_team_statistics(team_id, league_id, season)
        return results

    async def get_team_squad(self, team_id: int) -> list[dict[str, Any]]:
        """Fetch current national team squad roster."""
        cache_key = f"af:squad:{team_id}"
        return await self._cached_request(
            cache_key,
            "/players/squads",
            {"team": team_id},
            ttl_seconds=CACHE_TTL_STATS,
        )

    async def get_team_injuries(self, team_id: int) -> list[dict[str, Any]]:
        """Fetch reported injuries for a national team."""
        cache_key = f"af:injuries:{team_id}"
        return await self._cached_request(
            cache_key,
            "/injuries",
            {"team": team_id},
            ttl_seconds=CACHE_TTL_STATS,
        )

    async def get_team_transfers(self, team_id: int) -> list[dict[str, Any]]:
        """Fetch transfer history for a club."""
        cache_key = f"af:transfers:{team_id}"
        return await self._cached_request(
            cache_key,
            "/transfers",
            {"team": team_id},
            ttl_seconds=CACHE_TTL_STATS,
        )


_client: APIFootballClient | None = None


def get_api_football_client() -> APIFootballClient:
    """Return a shared APIFootballClient instance."""
    global _client
    if _client is None:
        _client = APIFootballClient()
    return _client
