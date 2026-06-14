"""Compute GoalMind team stats from StatsBomb match history."""

from __future__ import annotations

from typing import Any

from app.models.team import TeamStatsResponse
from app.services.data_sources.possession import team_possession_in_match
from app.services.data_sources.statsbomb import StatsBombRepository
from app.services.data_sources.team_flags import team_display_code, team_flag_url
from app.services.data_sources.team_names import normalize_team_name, stable_team_id


def _match_result_for_team(match: dict[str, Any], team_key: str) -> tuple[str, int, int]:
    """Return (W/D/L), goals_for, goals_against for a team in a match."""
    home_key = normalize_team_name(match["home_team"]["home_team_name"])
    away_key = normalize_team_name(match["away_team"]["away_team_name"])
    home_score = match.get("home_score", 0) or 0
    away_score = match.get("away_score", 0) or 0

    if team_key == home_key:
        goals_for, goals_against = home_score, away_score
    else:
        goals_for, goals_against = away_score, home_score

    if goals_for > goals_against:
        return "W", goals_for, goals_against
    if goals_for < goals_against:
        return "L", goals_for, goals_against
    return "D", goals_for, goals_against


async def _average_possession(
    repo: StatsBombRepository,
    team_name: str,
    history: list[dict[str, Any]],
) -> float | None:
    values: list[float] = []

    for match in history:
        possession_map = await repo.get_match_possession(match["match_id"])
        pct = team_possession_in_match(possession_map, team_name)
        if pct is not None:
            values.append(pct)

    if not values:
        return None

    return sum(values) / len(values)


async def compute_team_stats(
    repo: StatsBombRepository,
    team_name: str,
    *,
    team_id: int | None = None,
) -> TeamStatsResponse:
    """Derive prediction inputs from StatsBomb World Cup match history."""
    history = repo.team_match_history(team_name)
    resolved_id = team_id or repo.resolve_team_id(team_name)

    if not history:
        return TeamStatsResponse(
            team_id=resolved_id,
            name=team_name,
            code=team_display_code(team_name),
            logo=team_flag_url(team_name),
            recent_form=0.5,
            avg_goals_scored=1.2,
            avg_goals_conceded=1.2,
            possession_avg=50.0,
            form_string=None,
            matches_played=0,
        )

    team_key = normalize_team_name(team_name)
    results: list[tuple[str, int, int]] = [
        _match_result_for_team(m, team_key) for m in history
    ]

    recent = results[:5]
    form_chars = "".join(r[0] for r in recent)
    form_points = sum(1.0 if r[0] == "W" else 0.5 if r[0] == "D" else 0.0 for r in recent)
    recent_form = form_points / len(recent) if recent else 0.5

    total_gf = sum(r[1] for r in results)
    total_ga = sum(r[2] for r in results)
    played = len(results)
    possession_avg = await _average_possession(repo, team_name, history)

    return TeamStatsResponse(
        team_id=resolved_id,
        name=team_name,
        code=team_display_code(team_name),
        logo=team_flag_url(team_name),
        recent_form=recent_form,
        avg_goals_scored=total_gf / played,
        avg_goals_conceded=total_ga / played,
        possession_avg=possession_avg if possession_avg is not None else 50.0,
        form_string=form_chars,
        matches_played=played,
    )


def h2h_win_rate(
    repo: StatsBombRepository,
    team_a: str,
    team_b: str,
) -> tuple[float | None, int]:
    """Historical win rate for team_a vs team_b across loaded StatsBomb seasons."""
    matches = repo.h2h_matches(team_a, team_b)
    if not matches:
        return None, 0

    a_key = normalize_team_name(team_a)
    wins = 0

    for match in matches:
        result, _, _ = _match_result_for_team(match, a_key)
        if result == "W":
            wins += 1

    return wins / len(matches), len(matches)
