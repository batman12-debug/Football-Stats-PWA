"""TheSportsDB client for player photos (free tier)."""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from app.services.cache import get_json_cached, set_json_cached

logger = logging.getLogger(__name__)

TSDB_BASE = "https://www.thesportsdb.com/api/v1/json/3"
CACHE_TTL = 86400 * 7


class TheSportsDBClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(12.0, connect=4.0))

    async def close(self) -> None:
        await self._client.aclose()

    async def search_player_photo(self, player_name: str, team_name: str | None = None) -> str | None:
        """Return a headshot URL for a player, or None."""
        cache_key = f"tsdb:photo:{player_name.lower()}"
        cached = await get_json_cached(cache_key)
        if cached is not None:
            return cached or None

        query = player_name.replace(" ", "_")
        try:
            response = await self._client.get(
                f"{TSDB_BASE}/searchplayers.php",
                params={"p": query},
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.debug("TheSportsDB lookup failed for %s: %s", player_name, exc)
            await set_json_cached(cache_key, "", ttl_seconds=CACHE_TTL)
            return None

        players: list[dict[str, Any]] = data.get("player") or []
        photo = _pick_best_photo(players, player_name, team_name)
        await set_json_cached(cache_key, photo or "", ttl_seconds=CACHE_TTL)
        return photo


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower().strip())


def _pick_best_photo(
    players: list[dict[str, Any]],
    target_name: str,
    team_name: str | None,
) -> str | None:
    if not players:
        return None

    target = _normalize(target_name)
    target_last = target.split()[-1] if target else ""

    best: dict[str, Any] | None = None
    best_score = -1

    for player in players:
        name = _normalize(player.get("strPlayer") or "")
        if not name:
            continue

        score = 0
        if name == target:
            score += 10
        elif target in name or name in target:
            score += 6
        elif target_last and target_last in name:
            score += 4

        if team_name:
            team = _normalize(player.get("strTeam") or "")
            country = _normalize(player.get("strNationality") or "")
            if _normalize(team_name) in {team, country}:
                score += 3

        if score > best_score:
            best_score = score
            best = player

    if best is None or best_score <= 0:
        best = players[0]

    for key in ("strThumb", "strCutout", "strRender"):
        url = best.get(key)
        if url:
            return str(url)

    return None


_client: TheSportsDBClient | None = None


def get_thesportsdb_client() -> TheSportsDBClient:
    global _client
    if _client is None:
        _client = TheSportsDBClient()
    return _client
