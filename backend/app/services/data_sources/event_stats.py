"""Aggregate live match statistics from StatsBomb event streams."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.data_sources.possession import possession_from_events, team_possession_in_match
from app.services.data_sources.team_names import normalize_team_name

SHOTS_ON_TARGET = frozenset({"Goal", "Saved", "Saved to Post"})
INCOMPLETE_PASS_OUTCOMES = frozenset({"Incomplete", "Out", "Unknown", "Pass Offside"})


def _is_pass_completed(pass_data: dict[str, Any]) -> bool:
    """StatsBomb omits outcome on successful passes; only failures are tagged."""
    outcome_obj = pass_data.get("outcome")
    if outcome_obj is None:
        return True
    if isinstance(outcome_obj, dict):
        name = outcome_obj.get("name") or ""
        return name not in INCOMPLETE_PASS_OUTCOMES
    return True


@dataclass
class TeamLiveStats:
    shots: int = 0
    shots_on_target: int = 0
    possession: float = 50.0
    passes: int = 0
    passes_completed: int = 0
    fouls: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    offsides: int = 0
    corners: int = 0

    @property
    def pass_accuracy(self) -> float:
        if self.passes == 0:
            return 0.0
        return (self.passes_completed / self.passes) * 100.0


@dataclass
class MatchLiveStats:
    home: TeamLiveStats = field(default_factory=TeamLiveStats)
    away: TeamLiveStats = field(default_factory=TeamLiveStats)
    minute: int = 0


def _team_side(event: dict[str, Any], home_name: str, away_name: str) -> str | None:
    team = event.get("team", {}).get("name")
    if not team:
        return None
    key = normalize_team_name(team)
    if key == normalize_team_name(home_name):
        return "home"
    if key == normalize_team_name(away_name):
        return "away"
    return None


def _card_color(event: dict[str, Any]) -> str | None:
    for block in ("foul_committed", "bad_behaviour"):
        card = event.get(block, {}) or {}
        if isinstance(card, dict):
            name = (card.get("card") or {}).get("name", "")
            if name in ("Yellow Card", "Second Yellow"):
                return "yellow"
            if name == "Red Card":
                return "red"
    return None


def filter_events_by_minute(events: list[dict[str, Any]], max_minute: int) -> list[dict[str, Any]]:
    return [e for e in events if int(e.get("minute") or 0) <= max_minute]


def aggregate_match_stats(
    events: list[dict[str, Any]],
    home_name: str,
    away_name: str,
    *,
    max_minute: int | None = None,
) -> MatchLiveStats:
    """Build cumulative team stats from events, optionally capped at a match minute."""
    if max_minute is not None:
        events = filter_events_by_minute(events, max_minute)

    home = TeamLiveStats()
    away = TeamLiveStats()
    stats = {"home": home, "away": away}

    possession_map = possession_from_events(events)
    home_pct = team_possession_in_match(possession_map, home_name)
    away_pct = team_possession_in_match(possession_map, away_name)
    if home_pct is not None:
        home.possession = home_pct
    if away_pct is not None:
        away.possession = away_pct

    max_seen_minute = 0

    for event in events:
        minute = int(event.get("minute") or 0)
        max_seen_minute = max(max_seen_minute, minute)

        side = _team_side(event, home_name, away_name)
        if not side:
            continue

        team_stats: TeamLiveStats = stats[side]
        event_type = event.get("type", {}).get("name", "")

        if event_type == "Shot":
            team_stats.shots += 1
            outcome = (event.get("shot") or {}).get("outcome", {}).get("name", "")
            if outcome in SHOTS_ON_TARGET:
                team_stats.shots_on_target += 1

        elif event_type == "Pass":
            team_stats.passes += 1
            pass_data = event.get("pass") or {}
            if _is_pass_completed(pass_data):
                team_stats.passes_completed += 1
            pass_type = pass_data.get("type", {}).get("name", "")
            if pass_type == "Corner":
                team_stats.corners += 1

        elif event_type == "Foul Committed":
            team_stats.fouls += 1
            color = _card_color(event)
            if color == "yellow":
                team_stats.yellow_cards += 1
            elif color == "red":
                team_stats.red_cards += 1

        elif event_type == "Bad Behaviour":
            color = _card_color(event)
            if color == "yellow":
                team_stats.yellow_cards += 1
            elif color == "red":
                team_stats.red_cards += 1

        elif event_type == "Offside":
            team_stats.offsides += 1

    return MatchLiveStats(
        home=home,
        away=away,
        minute=max_seen_minute if max_minute is None else max_minute,
    )


def count_goals_from_events(
    events: list[dict[str, Any]],
    home_name: str,
    away_name: str,
    *,
    max_minute: int | None = None,
) -> tuple[int, int]:
    """Count goals for each side from StatsBomb shot events."""
    if max_minute is not None:
        events = filter_events_by_minute(events, max_minute)

    home_goals = 0
    away_goals = 0

    for event in events:
        if event.get("type", {}).get("name") != "Shot":
            continue
        outcome = (event.get("shot") or {}).get("outcome", {}).get("name", "")
        if outcome != "Goal":
            continue
        side = _team_side(event, home_name, away_name)
        if side == "home":
            home_goals += 1
        elif side == "away":
            away_goals += 1

    return home_goals, away_goals
