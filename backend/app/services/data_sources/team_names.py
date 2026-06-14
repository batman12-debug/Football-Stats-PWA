"""Normalize team names across data sources."""

import hashlib
import re

# Common name differences between openfootball and StatsBomb.
ALIASES: dict[str, str] = {
    "usa": "united states",
    "u.s.a.": "united states",
    "united states of america": "united states",
    "korea republic": "south korea",
    "south korea": "south korea",
    "korea": "south korea",
    "bosnia & herzegovina": "bosnia-herzegovina",
    "bosnia and herzegovina": "bosnia-herzegovina",
    "bosnia-herzegovina": "bosnia-herzegovina",
    "united states": "united states",
    "cote d'ivoire": "ivory coast",
    "côte d'ivoire": "ivory coast",
    "czech republic": "czechia",
    "dr congo": "congo dr",
    "democratic republic of the congo": "congo dr",
    "curacao": "curaçao",
    "cape verde": "cape verde islands",
    "iran": "iran",
}


def normalize_team_name(name: str) -> str:
    cleaned = re.sub(r"[^\w\s&'-]", "", name.lower().strip())
    cleaned = re.sub(r"\s+", " ", cleaned)
    return ALIASES.get(cleaned, cleaned)


def stable_team_id(name: str) -> int:
    """Deterministic ID for teams without a StatsBomb ID."""
    normalized = normalize_team_name(name)
    digest = hashlib.md5(normalized.encode(), usedforsecurity=False).hexdigest()
    return int(digest[:8], 16)
