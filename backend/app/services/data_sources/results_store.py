"""Persist match results for bracket progression."""

import json
import logging
from typing import Any

from app.services.cache import get_cached, redis_configured, set_cached

logger = logging.getLogger(__name__)

RESULT_TTL = 60 * 60 * 24 * 90  # 90 days
_memory_results: dict[int, dict[str, int]] = {}


def _key(fixture_id: int) -> str:
    return f"goalmind:result:{fixture_id}"


def get_memory_results() -> dict[int, tuple[int, int]]:
    return {
        fid: (data["home_goals"], data["away_goals"])
        for fid, data in _memory_results.items()
    }


async def get_result(fixture_id: int) -> dict[str, Any] | None:
    if fixture_id in _memory_results:
        return _memory_results[fixture_id]

    if not redis_configured():
        return None

    raw = await get_cached(_key(fixture_id))
    if not raw:
        return None
    try:
        data = json.loads(raw)
        _memory_results[fixture_id] = data
        return data
    except json.JSONDecodeError:
        return None


async def set_result(fixture_id: int, home_goals: int, away_goals: int) -> None:
    payload = {"home_goals": home_goals, "away_goals": away_goals}
    _memory_results[fixture_id] = payload

    if not redis_configured():
        return

    await set_cached(_key(fixture_id), json.dumps(payload), ttl_seconds=RESULT_TTL)


async def load_results_for_fixtures(
    fixture_ids: list[int],
) -> dict[int, tuple[int, int]]:
    """Load stored scores for known fixture IDs (memory first, then Redis)."""
    out: dict[int, tuple[int, int]] = dict(get_memory_results())
    for fid in fixture_ids:
        if fid in out:
            continue
        result = await get_result(fid)
        if result is None:
            continue
        try:
            out[fid] = (int(result["home_goals"]), int(result["away_goals"]))
        except (KeyError, TypeError, ValueError):
            continue
    return out
