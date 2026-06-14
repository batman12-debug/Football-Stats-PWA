"""OpenFootball worldcup.json — free public-domain WC schedules."""

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from app.config import settings
from app.services.cache import get_json_cached, set_json_cached
from app.services.data_sources.team_flags import team_display_code, team_flag_url
from app.services.data_sources.team_names import normalize_team_name, stable_team_id

logger = logging.getLogger(__name__)

OPENFOOTBALL_BASE = (
    "https://raw.githubusercontent.com/openfootball/worldcup.json/master"
)
CACHE_TTL = 600  # 10 minutes — refresh scores during the tournament
_BUNDLED_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_memory_tournament: dict[int, dict[str, Any]] = {}


class OpenFootballError(Exception):
    """Raised when openfootball data cannot be loaded."""


def _is_placeholder_team(name: str) -> bool:
    """Knockout placeholders like 1A, W74, L101."""
    return bool(re.match(r"^(\d+[A-L]|W\d+|L\d+)$", name.strip(), re.I))


def parse_kickoff(date_str: str, time_str: str) -> datetime:
    """Parse openfootball date/time into UTC datetime."""
    # e.g. date "2026-06-11", time "13:00 UTC-6"
    time_match = re.match(r"(\d{2}):(\d{2})\s*UTC([+-]?\d+)", time_str.strip())
    if time_match:
        hour, minute, offset = time_match.groups()
        utc_hour = int(hour) - int(offset)
        return datetime(
            int(date_str[:4]),
            int(date_str[5:7]),
            int(date_str[8:10]),
            utc_hour % 24,
            int(minute),
            tzinfo=timezone.utc,
        )

    return datetime.fromisoformat(f"{date_str}T12:00:00+00:00")


def fixture_id(match: dict[str, Any], index: int) -> int:
    """Stable numeric ID for an openfootball match."""
    if "num" in match:
        return 9_000_000 + int(match["num"])

    key = f"{match.get('date')}|{match.get('team1')}|{match.get('team2')}|{index}"
    digest = hashlib.md5(key.encode(), usedforsecurity=False).hexdigest()
    return 8_000_000 + int(digest[:7], 16) % 1_000_000


def _load_bundled_tournament(year: int) -> dict[str, Any] | None:
    path = _BUNDLED_DIR / f"worldcup_{year}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Bundled openfootball data unreadable at %s: %s", path, exc)
        return None


class OpenFootballClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=3.0))

    async def close(self) -> None:
        await self._client.aclose()

    async def get_all_matches(self) -> list[dict[str, Any]]:
        data = await self.get_tournament()
        return [{**m, "_index": i} for i, m in enumerate(data.get("matches", []))]

    async def get_tournament(self, year: int | None = None) -> dict[str, Any]:
        year = year or settings.openfootball_wc_year
        if year in _memory_tournament:
            return _memory_tournament[year]

        cache_key = f"of:wc:{year}"
        cached = await get_json_cached(cache_key)
        if cached is not None:
            _memory_tournament[year] = cached
            return cached

        url = f"{OPENFOOTBALL_BASE}/{year}/worldcup.json"
        try:
            response = await self._client.get(url)
            response.raise_for_status()
            data = response.json()
            logger.info("Fetched openfootball WC %s from GitHub", year)
        except httpx.HTTPError as exc:
            bundled = _load_bundled_tournament(year)
            if bundled is not None:
                logger.warning(
                    "OpenFootball GitHub fetch failed; using bundled WC %s data", year
                )
                _memory_tournament[year] = bundled
                return bundled
            raise OpenFootballError(f"Failed to load openfootball WC {year}") from exc

        _memory_tournament[year] = data
        await set_json_cached(cache_key, data, ttl_seconds=CACHE_TTL)
        return data

    async def get_group_stage_matches(self) -> list[dict[str, Any]]:
        data = await self.get_tournament()
        matches = data.get("matches", [])
        return [
            {**m, "_index": i}
            for i, m in enumerate(matches)
            if not _is_placeholder_team(m.get("team1", ""))
            and not _is_placeholder_team(m.get("team2", ""))
        ]

    async def get_upcoming_matches(self, limit: int = 10) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        upcoming: list[tuple[datetime, dict[str, Any]]] = []

        for match in await self.get_group_stage_matches():
            kickoff = parse_kickoff(match["date"], match.get("time", "12:00 UTC+0"))
            if kickoff >= now:
                upcoming.append((kickoff, match))

        upcoming.sort(key=lambda item: item[0])
        return [m for _, m in upcoming[:limit]]

    async def get_match_by_id(self, target_id: int) -> dict[str, Any] | None:
        for i, match in enumerate((await self.get_tournament()).get("matches", [])):
            indexed = {**match, "_index": i}
            if fixture_id(indexed, i) == target_id:
                return indexed
        return None

    async def list_teams(self) -> list[dict[str, Any]]:
        teams: dict[str, dict[str, Any]] = {}
        for match in await self.get_group_stage_matches():
            for side in ("team1", "team2"):
                name = match[side]
                key = normalize_team_name(name)
                if key not in teams:
                    teams[key] = {
                        "id": stable_team_id(name),
                        "name": name,
                        "code": team_display_code(name),
                        "logo": team_flag_url(name),
                    }
        return sorted(teams.values(), key=lambda t: t["name"])


_client: OpenFootballClient | None = None


def get_openfootball_client() -> OpenFootballClient:
    global _client
    if _client is None:
        _client = OpenFootballClient()
    return _client
