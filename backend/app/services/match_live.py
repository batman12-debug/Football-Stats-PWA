"""Live match detection and real-time statistics."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.models.match import LiveMatchStatsResponse, LiveTeamStats
from app.services.api_football import APIFootballError, get_api_football_client
from app.services.data_sources.event_stats import (
    MatchLiveStats,
    TeamLiveStats,
    aggregate_match_stats,
    count_goals_from_events,
)
from app.services.data_sources.espn_wc import (
    EspnTeamBoxStats,
    build_espn_wc_index,
    fetch_espn_match_boxscore,
    lookup_espn_match,
)
from app.services.data_sources.statsbomb import get_statsbomb_repository
from app.services.data_sources.team_names import normalize_team_name
from app.services.fixture_scores import (
    LIVE_STATUSES,
    _elapsed_minute,
    resolve_fixture_display,
    resolve_match_status,
)

logger = logging.getLogger(__name__)

MATCH_DURATION = timedelta(minutes=105)


def _live_team_stats_from_espn(stats: EspnTeamBoxStats) -> LiveTeamStats:
    return LiveTeamStats(
        shots=stats.shots,
        shots_on_target=stats.shots_on_target,
        possession=round(stats.possession, 1),
        passes=stats.passes,
        pass_accuracy=round(stats.pass_accuracy, 1),
        fouls=stats.fouls,
        yellow_cards=stats.yellow_cards,
        red_cards=stats.red_cards,
        offsides=stats.offsides,
        corners=stats.corners,
    )


async def _stats_from_espn(
    *,
    fixture_id: int,
    home_name: str,
    away_name: str,
    espn_event_id: str,
    status: str,
    home_goals: int | None,
    away_goals: int | None,
    live_minute: int | None,
) -> LiveMatchStatsResponse | None:
    """Real in-match stats from ESPN summary boxscore."""
    rows = await fetch_espn_match_boxscore(espn_event_id)
    if not rows:
        return None

    home_key = normalize_team_name(home_name)
    away_key = normalize_team_name(away_name)
    home_stats: EspnTeamBoxStats | None = None
    away_stats: EspnTeamBoxStats | None = None

    for team_name, team_stats in rows:
        key = normalize_team_name(team_name)
        if key == home_key:
            home_stats = team_stats
        elif key == away_key:
            away_stats = team_stats

    if home_stats is None or away_stats is None:
        home_stats, away_stats = rows[0][1], rows[1][1]

    return LiveMatchStatsResponse(
        fixture_id=fixture_id,
        is_live=status == "LIVE" or status in LIVE_STATUSES,
        status=status,
        minute=live_minute or 0,
        home_team=home_name,
        away_team=away_name,
        home_goals=home_goals,
        away_goals=away_goals,
        home=_live_team_stats_from_espn(home_stats),
        away=_live_team_stats_from_espn(away_stats),
    )


async def _stats_from_api_football(fixture_id: int) -> LiveMatchStatsResponse | None:
    if not settings.api_football_configured:
        return None

    client = get_api_football_client()
    try:
        rows = await client.get_fixture_statistics(fixture_id)
    except APIFootballError:
        return None

    if not rows:
        return None

    # API-Football returns list of {team, statistics: [{type, value}]}
    return _parse_api_football_statistics(fixture_id, rows)


def _parse_stat_value(value: str | int | None) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    cleaned = str(value).replace("%", "").strip()
    try:
        return int(float(cleaned))
    except ValueError:
        return 0


def _parse_api_football_statistics(
    fixture_id: int,
    rows: list[dict],
) -> LiveMatchStatsResponse | None:
    if len(rows) < 2:
        return None

    def extract(team_row: dict) -> LiveTeamStats:
        mapping = {
            stat["type"]: stat.get("value")
            for stat in team_row.get("statistics", [])
            if stat.get("type")
        }
        passes = _parse_stat_value(mapping.get("Total passes"))
        accurate = _parse_stat_value(mapping.get("Passes accurate"))
        accuracy = _parse_stat_value(mapping.get("Passes %"))
        if accuracy == 0 and passes > 0:
            accuracy = round((accurate / passes) * 100, 1)

        return LiveTeamStats(
            shots=_parse_stat_value(mapping.get("Total Shots")),
            shots_on_target=_parse_stat_value(mapping.get("Shots on Goal")),
            possession=float(_parse_stat_value(mapping.get("Ball Possession"))),
            passes=passes,
            pass_accuracy=float(accuracy),
            fouls=_parse_stat_value(mapping.get("Fouls")),
            yellow_cards=_parse_stat_value(mapping.get("Yellow Cards")),
            red_cards=_parse_stat_value(mapping.get("Red Cards")),
            offsides=_parse_stat_value(mapping.get("Offsides")),
            corners=_parse_stat_value(mapping.get("Corner Kicks")),
        )

    home_row, away_row = rows[0], rows[1]
    return LiveMatchStatsResponse(
        fixture_id=fixture_id,
        is_live=True,
        status="LIVE",
        minute=0,
        home_team=home_row.get("team", {}).get("name", "Home"),
        away_team=away_row.get("team", {}).get("name", "Away"),
        home_goals=None,
        away_goals=None,
        home=extract(home_row),
        away=extract(away_row),
    )


async def _find_statsbomb_reference_match(home: str, away: str) -> int | None:
    repo = await get_statsbomb_repository()
    h2h = repo.h2h_matches(home, away)
    if h2h:
        return h2h[0]["match_id"]

    for match in repo.team_match_history(home):
        for side in ("home_team", "away_team"):
            other = match[side][f"{side.split('_')[0]}_team_name"]
            if normalize_team_name(other) == normalize_team_name(away):
                return match["match_id"]

    return None


async def _team_stats_from_latest_match(
    repo,
    team_name: str,
    minute: int,
) -> TeamLiveStats:
    history = repo.team_match_history(team_name)
    if not history:
        return TeamLiveStats()

    match = history[0]
    events = await repo.get_match_events(match["match_id"])
    if not events:
        return TeamLiveStats()

    home_name = match["home_team"]["home_team_name"]
    away_name = match["away_team"]["away_team_name"]
    aggregated = aggregate_match_stats(events, home_name, away_name, max_minute=minute)

    if normalize_team_name(home_name) == normalize_team_name(team_name):
        return aggregated.home
    return aggregated.away


async def _stats_from_statsbomb_replay(
    *,
    fixture_id: int,
    home_name: str,
    away_name: str,
    kickoff: datetime,
    status: str,
    home_goals: int | None,
    away_goals: int | None,
    live_minute: int | None = None,
) -> LiveMatchStatsResponse | None:
    repo = await get_statsbomb_repository()
    if live_minute is not None:
        minute = live_minute
    elif status == "LIVE" or status in LIVE_STATUSES:
        minute = _elapsed_minute(kickoff)
    else:
        minute = 90
    match_id = await _find_statsbomb_reference_match(home_name, away_name)

    if match_id is not None:
        events = await repo.get_match_events(match_id)
        if events:
            stats = aggregate_match_stats(events, home_name, away_name, max_minute=minute)
            ref = repo.get_match(match_id)
            if ref:
                ref_home = ref["home_team"]["home_team_name"]
                if normalize_team_name(ref_home) != normalize_team_name(home_name):
                    stats.home, stats.away = stats.away, stats.home
                    replay_home, replay_away = away_name, home_name
                else:
                    replay_home, replay_away = home_name, away_name
            else:
                replay_home, replay_away = home_name, away_name

            if home_goals is None or away_goals is None:
                hg, ag = count_goals_from_events(
                    events, replay_home, replay_away, max_minute=minute
                )
                home_goals, away_goals = hg, ag
        else:
            stats = MatchLiveStats()
    else:
        # No H2H: blend each team's latest World Cup match events up to the elapsed minute
        stats = MatchLiveStats(
            home=await _team_stats_from_latest_match(repo, home_name, minute),
            away=await _team_stats_from_latest_match(repo, away_name, minute),
            minute=minute,
        )

    return LiveMatchStatsResponse(
        fixture_id=fixture_id,
        is_live=status == "LIVE" or status in LIVE_STATUSES,
        status=status,
        minute=minute,
        home_team=home_name,
        away_team=away_name,
        home_goals=home_goals,
        away_goals=away_goals,
        home=LiveTeamStats(
            shots=stats.home.shots,
            shots_on_target=stats.home.shots_on_target,
            possession=round(stats.home.possession, 1),
            passes=stats.home.passes,
            pass_accuracy=round(stats.home.pass_accuracy, 1),
            fouls=stats.home.fouls,
            yellow_cards=stats.home.yellow_cards,
            red_cards=stats.home.red_cards,
            offsides=stats.home.offsides,
            corners=stats.home.corners,
        ),
        away=LiveTeamStats(
            shots=stats.away.shots,
            shots_on_target=stats.away.shots_on_target,
            possession=round(stats.away.possession, 1),
            passes=stats.away.passes,
            pass_accuracy=round(stats.away.pass_accuracy, 1),
            fouls=stats.away.fouls,
            yellow_cards=stats.away.yellow_cards,
            red_cards=stats.away.red_cards,
            offsides=stats.away.offsides,
            corners=stats.away.corners,
        ),
    )


async def get_live_match_stats(fixture_id: int) -> LiveMatchStatsResponse:
    """Return live stats for an in-progress fixture."""
    from app.services.football_data import ResourceNotFoundError, _find_bracket_fixture

    fixture = await _find_bracket_fixture(fixture_id)
    if not fixture:
        raise ResourceNotFoundError(f"Fixture {fixture_id} not found")

    status, home_goals, away_goals, live_minute = await resolve_fixture_display(
        fixture_id=fixture_id,
        kickoff=fixture.date,
        stored_status=fixture.status,
        stored_home_goals=fixture.home_goals,
        stored_away_goals=fixture.away_goals,
        home_name=fixture.home_team.name,
        away_name=fixture.away_team.name,
    )
    is_live = status == "LIVE" or status in LIVE_STATUSES

    if not is_live:
        return LiveMatchStatsResponse(
            fixture_id=fixture_id,
            is_live=False,
            status=status,
            minute=0,
            home_team=fixture.home_team.name,
            away_team=fixture.away_team.name,
            home_goals=home_goals,
            away_goals=away_goals,
            home=LiveTeamStats(),
            away=LiveTeamStats(),
        )

    # ESPN boxscore — real live stats in hybrid mode (scores already use ESPN)
    espn_index = await build_espn_wc_index()
    espn_match = lookup_espn_match(
        espn_index,
        home_name=fixture.home_team.name,
        away_name=fixture.away_team.name,
        kickoff=fixture.date,
    )
    if espn_match and (espn_match.is_live or status in LIVE_STATUSES):
        espn_stats = await _stats_from_espn(
            fixture_id=fixture_id,
            home_name=fixture.home_team.name,
            away_name=fixture.away_team.name,
            espn_event_id=espn_match.espn_event_id,
            status=status,
            home_goals=home_goals if home_goals is not None else espn_match.home_goals,
            away_goals=away_goals if away_goals is not None else espn_match.away_goals,
            live_minute=live_minute or espn_match.minute,
        )
        if espn_stats:
            return espn_stats

    # API-Football when configured with matching fixture IDs
    api_stats = await _stats_from_api_football(fixture_id)
    if api_stats:
        api_stats.home_team = fixture.home_team.name
        api_stats.away_team = fixture.away_team.name
        api_stats.home_goals = home_goals
        api_stats.away_goals = away_goals
        api_stats.minute = live_minute or _elapsed_minute(fixture.date)
        api_stats.status = status
        return api_stats

    # StatsBomb replay — fallback when ESPN/API-Football unavailable
    replay = await _stats_from_statsbomb_replay(
        fixture_id=fixture_id,
        home_name=fixture.home_team.name,
        away_name=fixture.away_team.name,
        kickoff=fixture.date,
        status=status,
        home_goals=home_goals,
        away_goals=away_goals,
        live_minute=live_minute,
    )
    if replay and live_minute is not None:
        replay.minute = live_minute
    return replay
