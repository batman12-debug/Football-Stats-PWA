"""Map OpenFootball / app team names to API-Football national team IDs."""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "api_football_team_ids.json"

# Fallback IDs when the bundled map is incomplete.
_FALLBACK_IDS: dict[str, int] = {
    "Bosnia & Herzegovina": 1113,
    "Senegal": 13,
    "South Africa": 1531,
    "South Korea": 17,
    "Spain": 9,
    "Sweden": 5,
    "Switzerland": 15,
    "Tunisia": 28,
    "Turkey": 777,
    "USA": 2384,
    "Uruguay": 7,
    "Uzbekistan": 1568,
}

_mapping: dict[str, int | None] | None = None


def _load_mapping() -> dict[str, int | None]:
    global _mapping
    if _mapping is not None:
        return _mapping

    merged: dict[str, int | None] = dict(_FALLBACK_IDS)
    if _DATA_PATH.is_file():
        try:
            raw = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
            merged.update(raw)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not read API team ID map: %s", exc)

    _mapping = merged
    return _mapping


def resolve_api_football_team_id(team_name: str) -> int | None:
    """Return API-Football national team ID for a tournament team name."""
    mapping = _load_mapping()
    team_id = mapping.get(team_name)
    if team_id is not None:
        return int(team_id)
    return _FALLBACK_IDS.get(team_name)
