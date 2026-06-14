"""Possession percentages from StatsBomb event durations."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.services.data_sources.team_names import normalize_team_name


def possession_from_events(events: list[dict[str, Any]]) -> dict[str, float]:
    """
    Estimate each team's share of possession from event durations.

    StatsBomb attributes duration to the team in possession for each event.
    """
    duration_by_team: dict[str, float] = defaultdict(float)
    total_duration = 0.0

    for event in events:
        duration = event.get("duration")
        if duration is None:
            continue

        possession_team = event.get("possession_team")
        if not possession_team:
            continue

        name = possession_team.get("name")
        if not name:
            continue

        seconds = float(duration)
        if seconds <= 0:
            continue

        duration_by_team[name] += seconds
        total_duration += seconds

    if total_duration <= 0:
        return {}

    return {
        name: (seconds / total_duration) * 100.0
        for name, seconds in duration_by_team.items()
    }


def team_possession_in_match(
    possession_map: dict[str, float],
    team_name: str,
) -> float | None:
    """Look up a team's possession % using normalized name matching."""
    if not possession_map:
        return None

    target = normalize_team_name(team_name)
    for name, pct in possession_map.items():
        if normalize_team_name(name) == target:
            return pct

    return None
