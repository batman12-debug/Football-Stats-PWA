"""StatsBomb Open Data client — https://github.com/statsbomb/open-data"""

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import settings
from app.services.cache import get_json_cached, set_json_cached
from app.services.data_sources.possession import possession_from_events
from app.services.data_sources.team_names import normalize_team_name, stable_team_id

logger = logging.getLogger(__name__)

STATSBOMB_BASE = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
CACHE_TTL = 86400  # 24h — open data changes infrequently


class StatsBombError(Exception):
    """Raised when StatsBomb open data cannot be loaded."""


class StatsBombClient:
    """Fetch and cache StatsBomb JSON from GitHub."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=60.0)

    async def close(self) -> None:
        await self._client.aclose()

    async def _fetch_json(self, path: str) -> Any:
        cache_key = f"sb:{path}"
        cached = await get_json_cached(cache_key)
        if cached is not None:
            return cached

        url = f"{STATSBOMB_BASE}/{path}"
        try:
            response = await self._client.get(url)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            raise StatsBombError(f"Failed to fetch StatsBomb data at {path}") from exc

        await set_json_cached(cache_key, data, ttl_seconds=CACHE_TTL)
        return data

    async def get_competitions(self) -> list[dict[str, Any]]:
        return await self._fetch_json("competitions.json")

    async def get_matches(self, competition_id: int, season_id: int) -> list[dict[str, Any]]:
        return await self._fetch_json(f"matches/{competition_id}/{season_id}.json")

    async def get_events(self, match_id: int) -> list[dict[str, Any]]:
        return await self._fetch_json(f"events/{match_id}.json")

    async def get_lineups(self, match_id: int) -> list[dict[str, Any]]:
        return await self._fetch_json(f"lineups/{match_id}.json")


_client: StatsBombClient | None = None


def get_statsbomb_client() -> StatsBombClient:
    global _client
    if _client is None:
        _client = StatsBombClient()
    return _client


class StatsBombRepository:
    """In-memory index built from StatsBomb World Cup match files."""

    def __init__(self) -> None:
        self._matches: list[dict[str, Any]] = []
        self._matches_by_id: dict[int, dict[str, Any]] = {}
        self._team_name_to_id: dict[str, int] = {}
        self._team_id_to_name: dict[int, str] = {}
        self._possession_by_match: dict[int, dict[str, float]] = {}
        self._match_events: dict[int, list[dict[str, Any]]] = {}
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    async def load(self) -> None:
        if self._loaded:
            return

        client = get_statsbomb_client()
        competition_id = settings.statsbomb_competition_id

        for season_id in settings.statsbomb_season_id_list:
            try:
                matches = await client.get_matches(competition_id, season_id)
                self._matches.extend(matches)
                logger.info(
                    "Loaded %d StatsBomb matches (competition=%s season=%s)",
                    len(matches),
                    competition_id,
                    season_id,
                )
            except StatsBombError as exc:
                logger.warning("StatsBomb season %s unavailable: %s", season_id, exc)

        for match in self._matches:
            match_id = match["match_id"]
            self._matches_by_id[match_id] = match

            home_name = match["home_team"]["home_team_name"]
            away_name = match["away_team"]["away_team_name"]
            home_id = match["home_team"]["home_team_id"]
            away_id = match["away_team"]["away_team_id"]

            self._register_team(home_name, home_id)
            self._register_team(away_name, away_id)

        self._loaded = True

    def _register_team(self, name: str, team_id: int) -> None:
        key = normalize_team_name(name)
        self._team_name_to_id[key] = team_id
        self._team_id_to_name[team_id] = name

    def resolve_team_id(self, name: str) -> int:
        key = normalize_team_name(name)
        return self._team_name_to_id.get(key, stable_team_id(name))

    def resolve_team_name(self, team_id: int, fallback: str = "Unknown") -> str:
        return self._team_id_to_name.get(team_id, fallback)

    def get_match(self, match_id: int) -> dict[str, Any] | None:
        return self._matches_by_id.get(match_id)

    def all_matches(self) -> list[dict[str, Any]]:
        return list(self._matches)

    def teams_from_matches(self) -> list[tuple[int, str]]:
        seen: set[int] = set()
        teams: list[tuple[int, str]] = []
        for team_id, name in sorted(self._team_id_to_name.items(), key=lambda x: x[1]):
            if team_id not in seen:
                seen.add(team_id)
                teams.append((team_id, name))
        return teams

    def h2h_matches(self, team_a: str, team_b: str) -> list[dict[str, Any]]:
        a = normalize_team_name(team_a)
        b = normalize_team_name(team_b)
        results: list[dict[str, Any]] = []

        for match in self._matches:
            home = normalize_team_name(match["home_team"]["home_team_name"])
            away = normalize_team_name(match["away_team"]["away_team_name"])
            if {home, away} == {a, b}:
                results.append(match)
        return results

    async def get_match_events(self, match_id: int) -> list[dict[str, Any]]:
        """Cached full event list for a match."""
        if match_id in self._match_events:
            return self._match_events[match_id]

        client = get_statsbomb_client()
        try:
            events = await client.get_events(match_id)
        except StatsBombError:
            self._match_events[match_id] = []
            return []

        self._match_events[match_id] = events
        return events

    async def get_match_possession(self, match_id: int) -> dict[str, float]:
        """Cached possession split for a match (team name -> %)."""
        if match_id in self._possession_by_match:
            return self._possession_by_match[match_id]

        events = await self.get_match_events(match_id)
        result = possession_from_events(events)
        self._possession_by_match[match_id] = result
        return result

    async def get_team_lineup_roles(
        self, team_name: str
    ) -> tuple[list[str], list[str]]:
        """Return (starting_xi_names, bench_names) from the most recent WC match."""
        history = self.team_match_history(team_name)
        if not history:
            return [], []

        client = get_statsbomb_client()
        key = normalize_team_name(team_name)

        for match in history:
            match_id = match["match_id"]
            try:
                lineups = await client.get_lineups(match_id)
            except StatsBombError:
                continue

            for team_lineup in lineups:
                lu_name = normalize_team_name(team_lineup.get("team_name", ""))
                if lu_name != key:
                    continue

                starters: list[str] = []
                bench: list[str] = []
                for player in team_lineup.get("lineup", []):
                    name = player.get("player_name", "")
                    positions = player.get("positions") or []
                    kicked_off = any(
                        str(pos.get("from", "")).startswith("00:")
                        for pos in positions
                    )
                    if kicked_off:
                        starters.append(name)
                    else:
                        bench.append(name)

                if starters:
                    return starters[:11], bench

        return [], []

    def team_match_history(self, team_name: str) -> list[dict[str, Any]]:
        key = normalize_team_name(team_name)
        history: list[dict[str, Any]] = []

        for match in self._matches:
            home = normalize_team_name(match["home_team"]["home_team_name"])
            away = normalize_team_name(match["away_team"]["away_team_name"])
            if key in {home, away}:
                history.append(match)

        history.sort(
            key=lambda m: f"{m['match_date']}T{m.get('kick_off', '00:00:00')}",
            reverse=True,
        )
        return history


_repository: StatsBombRepository | None = None


async def get_statsbomb_repository() -> StatsBombRepository:
    global _repository
    if _repository is None:
        _repository = StatsBombRepository()
    await _repository.load()
    return _repository
