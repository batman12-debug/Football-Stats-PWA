"""Football data facade — routes to free open data or API-Football."""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.models.match import (
    BracketFixtureSummary,
    FixtureDetailResponse,
    FixtureSummary,
    TournamentBracketResponse,
)
from app.models.prediction import PredictionResponse
from app.models.player import TeamSquadResponse
from app.models.team import TeamStatsResponse, TeamSummary
from app.services.api_football import (
    WC_LEAGUE_ID,
    WC_SEASON,
    APIFootballError,
    get_api_football_client,
)
from app.services.data_sources.aggregator import compute_team_stats, h2h_win_rate
from app.services.data_sources.bracket import build_tournament_bracket
from app.services.data_sources.results_store import get_memory_results, set_result
from app.services.data_sources.openfootball import (
    OpenFootballError,
    fixture_id as openfootball_fixture_id,
    get_openfootball_client,
    parse_kickoff,
)
from app.services.data_sources.statsbomb import (
    StatsBombError,
    get_statsbomb_repository,
)
from app.services.data_sources.squad import build_team_squad
from app.services.data_sources.team_flags import team_display_code, team_flag_url
from app.services.data_sources.team_names import stable_team_id
from app.services.prediction_engine import TeamInput, predict_match

UPCOMING_STATUSES = {"NS", "TBD", "PST"}

_bracket_cache: TournamentBracketResponse | None = None
_bracket_cache_at: float = 0.0
_BRACKET_CACHE_TTL = 300.0


async def _enrich_bracket_fixture(
    fixture: BracketFixtureSummary,
    *,
    espn_index: dict | None = None,
) -> BracketFixtureSummary:
    """Attach live/finished status and scores for started fixtures."""
    if not fixture.home_resolved or not fixture.away_resolved:
        return fixture

    from app.services.fixture_scores import resolve_fixture_display

    kickoff = fixture.date
    if kickoff.tzinfo is None:
        kickoff = kickoff.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    if (
        kickoff > now
        and fixture.status in {"NS", "TBD"}
        and fixture.home_goals is None
        and fixture.away_goals is None
    ):
        return fixture

    status, home_goals, away_goals, _minute = await resolve_fixture_display(
        fixture_id=fixture.id,
        kickoff=fixture.date,
        stored_status=fixture.status,
        stored_home_goals=fixture.home_goals,
        stored_away_goals=fixture.away_goals,
        home_name=fixture.home_team.name,
        away_name=fixture.away_team.name,
        espn_index=espn_index,
    )
    return fixture.model_copy(
        update={
            "status": status,
            "home_goals": home_goals,
            "away_goals": away_goals,
        }
    )


async def _enrich_bracket(bracket: TournamentBracketResponse) -> TournamentBracketResponse:
    """Apply live/finished scores to every resolvable fixture in the bracket."""
    from app.services.data_sources.espn_wc import build_espn_wc_index

    espn_index = await build_espn_wc_index()
    stages_out = []
    for stage in bracket.stages:
        if stage.groups:
            groups_out = []
            for group in stage.groups:
                fixtures = await asyncio.gather(
                    *(
                        _enrich_bracket_fixture(f, espn_index=espn_index)
                        for f in group.fixtures
                    )
                )
                groups_out.append(group.model_copy(update={"fixtures": list(fixtures)}))
            stages_out.append(stage.model_copy(update={"groups": groups_out}))
        else:
            fixtures = await asyncio.gather(
                *(
                    _enrich_bracket_fixture(f, espn_index=espn_index)
                    for f in stage.fixtures
                )
            )
            stages_out.append(stage.model_copy(update={"fixtures": list(fixtures)}))

    return bracket.model_copy(update={"stages": stages_out})


class ResourceNotFoundError(Exception):
    """Raised when a requested football resource does not exist."""


class FootballDataError(Exception):
    """Raised when the configured data source is unavailable."""


# ---------------------------------------------------------------------------
# API-Football transforms (legacy / paid tier)
# ---------------------------------------------------------------------------

def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_form(form: str | None) -> tuple[float, str | None]:
    if not form:
        return 0.5, None
    recent = form.strip()[-5:]
    if not recent:
        return 0.5, form
    points = sum(
        1.0 if char == "W" else 0.5 if char == "D" else 0.0
        for char in recent.upper()
    )
    return points / len(recent), form


def _extract_possession(raw_stats: dict[str, Any]) -> float:
    for key in ("possession", "ball_possession"):
        if key in raw_stats:
            return _safe_float(raw_stats[key], 50.0)
    return 50.0


def transform_team_summary(entry: dict[str, Any]) -> TeamSummary:
    team = entry.get("team", entry)
    return TeamSummary(
        id=team["id"],
        name=team["name"],
        code=team.get("code"),
        logo=team.get("logo"),
    )


def transform_team_stats(raw_stats: dict[str, Any]) -> TeamStatsResponse:
    team = raw_stats.get("team", {})
    goals = raw_stats.get("goals", {})
    fixtures = raw_stats.get("fixtures", {})
    recent_form, form_string = _parse_form(raw_stats.get("form"))
    goals_for = goals.get("for", {}).get("average", {})
    goals_against = goals.get("against", {}).get("average", {})
    played = fixtures.get("played", {})
    return TeamStatsResponse(
        team_id=team.get("id", 0),
        name=team.get("name", "Unknown"),
        code=team.get("code"),
        logo=team.get("logo"),
        recent_form=recent_form,
        avg_goals_scored=_safe_float(goals_for.get("total"), 0.0),
        avg_goals_conceded=_safe_float(goals_against.get("total"), 0.0),
        possession_avg=_extract_possession(raw_stats),
        form_string=form_string,
        matches_played=int(played.get("total") or 0),
    )


def transform_fixture(raw_fixture: dict[str, Any]) -> FixtureSummary:
    fixture = raw_fixture["fixture"]
    teams = raw_fixture["teams"]
    goals = raw_fixture.get("goals", {})
    venue = fixture.get("venue") or {}
    venue_name = venue.get("name")
    venue_city = venue.get("city")
    venue_label = f"{venue_name}, {venue_city}" if venue_name and venue_city else venue_name
    return FixtureSummary(
        id=fixture["id"],
        date=datetime.fromisoformat(fixture["date"].replace("Z", "+00:00")),
        status=fixture["status"]["short"],
        home_team=TeamSummary(
            id=teams["home"]["id"],
            name=teams["home"]["name"],
            logo=teams["home"].get("logo"),
        ),
        away_team=TeamSummary(
            id=teams["away"]["id"],
            name=teams["away"]["name"],
            logo=teams["away"].get("logo"),
        ),
        home_goals=goals.get("home"),
        away_goals=goals.get("away"),
        venue=venue_label,
    )


def _transform_openfootball_match(match: dict[str, Any]) -> FixtureSummary:
    index = match.get("_index", 0)
    home_name = match["team1"]
    away_name = match["team2"]
    return FixtureSummary(
        id=openfootball_fixture_id(match, index),
        date=parse_kickoff(match["date"], match.get("time", "12:00 UTC+0")),
        status="NS",
        home_team=TeamSummary(
            id=stable_team_id(home_name),
            name=home_name,
            code=team_display_code(home_name),
            logo=team_flag_url(home_name),
        ),
        away_team=TeamSummary(
            id=stable_team_id(away_name),
            name=away_name,
            code=team_display_code(away_name),
            logo=team_flag_url(away_name),
        ),
        home_goals=None,
        away_goals=None,
        venue=match.get("ground"),
    )


def _team_input(stats: TeamStatsResponse, h2h_rate: float | None) -> TeamInput:
    return TeamInput(
        recent_form=stats.recent_form,
        avg_goals_scored=stats.avg_goals_scored,
        avg_goals_conceded=stats.avg_goals_conceded,
        h2h_win_rate=h2h_rate,
        possession_avg=stats.possession_avg,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def list_teams() -> list[TeamSummary]:
    if settings.use_api_football:
        return await _list_teams_api_football()
    return await _list_teams_hybrid()


async def get_team_stats(team_id: int) -> TeamStatsResponse:
    if settings.use_api_football:
        return await _get_team_stats_api_football(team_id)
    return await _get_team_stats_hybrid(team_id)


async def get_team_squad(team_id: int) -> TeamSquadResponse:
    team_name = await _resolve_team_name(team_id)
    return await build_team_squad(team_id, team_name)


async def _resolve_team_name(team_id: int) -> str:
    if settings.use_api_football:
        teams = await _list_teams_api_football()
        for team in teams:
            if team.id == team_id:
                return team.name
        raise ResourceNotFoundError(f"Team {team_id} not found")

    repo = await get_statsbomb_repository()
    for _, name in repo.teams_from_matches():
        if repo.resolve_team_id(name) == team_id or stable_team_id(name) == team_id:
            return name

    of_client = get_openfootball_client()
    for team in await of_client.list_teams():
        if team["id"] == team_id:
            return team["name"]

    raise ResourceNotFoundError(f"Team {team_id} not found")


async def list_upcoming_fixtures(limit: int = 10) -> list[FixtureSummary]:
    if settings.use_api_football:
        return await _list_upcoming_api_football(limit)
    return await _list_upcoming_hybrid(limit)


async def get_fixture_detail(fixture_id: int) -> FixtureDetailResponse:
    if settings.use_api_football:
        return await _get_fixture_detail_api_football(fixture_id)
    return await _get_fixture_detail_hybrid(fixture_id)


async def get_prediction(fixture_id: int) -> PredictionResponse:
    if settings.use_api_football:
        return await _get_prediction_api_football(fixture_id)
    return await _get_prediction_hybrid(fixture_id)


async def get_tournament_bracket(*, force_refresh: bool = False) -> TournamentBracketResponse:
    global _bracket_cache, _bracket_cache_at

    if settings.use_api_football:
        raise FootballDataError("Tournament bracket is only available in hybrid mode")

    now = time.monotonic()
    if (
        not force_refresh
        and _bracket_cache is not None
        and now - _bracket_cache_at < _BRACKET_CACHE_TTL
    ):
        return await _enrich_bracket(_bracket_cache)

    raw = await get_openfootball_client().get_all_matches()
    data = await build_tournament_bracket(raw, stored_results=get_memory_results())
    _bracket_cache = await _enrich_bracket(TournamentBracketResponse(**data))
    _bracket_cache_at = now
    return _bracket_cache


async def record_match_result(fixture_id: int, home_goals: int, away_goals: int) -> None:
    global _bracket_cache, _bracket_cache_at
    await set_result(fixture_id, home_goals, away_goals)
    _bracket_cache = None
    _bracket_cache_at = 0.0


async def _find_bracket_fixture(fixture_id: int) -> BracketFixtureSummary | None:
    bracket = await get_tournament_bracket()
    for stage in bracket.stages:
        if stage.groups:
            for group in stage.groups:
                for fixture in group.fixtures:
                    if fixture.id == fixture_id:
                        return fixture
        for fixture in stage.fixtures:
            if fixture.id == fixture_id:
                return fixture
    return None


def _bracket_to_summary(fixture: BracketFixtureSummary) -> FixtureSummary:
    return FixtureSummary(
        id=fixture.id,
        date=fixture.date,
        status=fixture.status,
        home_team=TeamSummary(
            id=fixture.home_team.id or stable_team_id(fixture.home_team.name),
            name=fixture.home_team.name,
            code=fixture.home_team.code,
            logo=fixture.home_team.logo,
        ),
        away_team=TeamSummary(
            id=fixture.away_team.id or stable_team_id(fixture.away_team.name),
            name=fixture.away_team.name,
            code=fixture.away_team.code,
            logo=fixture.away_team.logo,
        ),
        home_goals=fixture.home_goals,
        away_goals=fixture.away_goals,
        venue=fixture.venue,
        goal_scorers=fixture.goal_scorers,
    )


# ---------------------------------------------------------------------------
# Hybrid: OpenFootball (2026 schedule) + StatsBomb (historical stats)
# ---------------------------------------------------------------------------

async def _list_teams_hybrid() -> list[TeamSummary]:
    try:
        of_client = get_openfootball_client()
        teams = await of_client.list_teams()
        return [TeamSummary(**t) for t in teams]
    except OpenFootballError as exc:
        raise FootballDataError(str(exc)) from exc


async def _get_team_stats_hybrid(team_id: int) -> TeamStatsResponse:
    repo = await get_statsbomb_repository()

    for _, name in repo.teams_from_matches():
        if repo.resolve_team_id(name) == team_id or stable_team_id(name) == team_id:
            return await compute_team_stats(repo, name, team_id=team_id)

    of_client = get_openfootball_client()
    for team in await of_client.list_teams():
        if team["id"] == team_id:
            return await compute_team_stats(repo, team["name"], team_id=team_id)

    raise ResourceNotFoundError(f"Team {team_id} not found")


async def _list_upcoming_hybrid(limit: int) -> list[FixtureSummary]:
    try:
        bracket = await get_tournament_bracket()
        upcoming: list[FixtureSummary] = []
        for stage in bracket.stages:
            pools = stage.groups or []
            for group in pools:
                for fixture in group.fixtures:
                    if fixture.status == "NS" and fixture.home_resolved and fixture.away_resolved:
                        upcoming.append(_bracket_to_summary(fixture))
            for fixture in stage.fixtures:
                if fixture.status == "NS" and fixture.home_resolved and fixture.away_resolved:
                    upcoming.append(_bracket_to_summary(fixture))
        upcoming.sort(key=lambda f: f.date)
        return upcoming[:limit]
    except OpenFootballError as exc:
        raise FootballDataError(str(exc)) from exc


async def _get_fixture_detail_hybrid(fixture_id: int) -> FixtureDetailResponse:
    from app.services.fixture_scores import LIVE_STATUSES, resolve_fixture_display

    bracket_fixture = await _find_bracket_fixture(fixture_id)
    if not bracket_fixture:
        raise ResourceNotFoundError(f"Fixture {fixture_id} not found")

    summary = _bracket_to_summary(bracket_fixture)

    if (
        bracket_fixture.status in LIVE_STATUSES
        and bracket_fixture.home_goals is not None
        and bracket_fixture.away_goals is not None
    ):
        summary.status = bracket_fixture.status
        summary.home_goals = bracket_fixture.home_goals
        summary.away_goals = bracket_fixture.away_goals
    else:
        status, home_goals, away_goals, _minute = await resolve_fixture_display(
            fixture_id=fixture_id,
            kickoff=summary.date,
            stored_status=summary.status,
            stored_home_goals=summary.home_goals,
            stored_away_goals=summary.away_goals,
            home_name=summary.home_team.name,
            away_name=summary.away_team.name,
        )
        summary.status = status
        summary.home_goals = home_goals
        summary.away_goals = away_goals

    is_live = summary.status in LIVE_STATUSES or summary.status == "LIVE"

    if is_live:
        home_stats = _minimal_team_stats(summary.home_team)
        away_stats = _minimal_team_stats(summary.away_team)
    else:
        repo = await get_statsbomb_repository()
        home_stats, away_stats = await asyncio.gather(
            compute_team_stats(repo, summary.home_team.name, team_id=summary.home_team.id),
            compute_team_stats(repo, summary.away_team.name, team_id=summary.away_team.id),
        )

    return FixtureDetailResponse(
        **summary.model_dump(),
        home_stats=home_stats,
        away_stats=away_stats,
    )


def _minimal_team_stats(team: TeamSummary) -> TeamStatsResponse:
    """Placeholder stats for live fixtures — avoids slow StatsBomb aggregation."""
    return TeamStatsResponse(
        team_id=team.id,
        name=team.name,
        code=team.code,
        logo=team.logo,
        recent_form=0.5,
        avg_goals_scored=0.0,
        avg_goals_conceded=0.0,
        possession_avg=50.0,
        form_string=None,
        matches_played=0,
    )


async def _get_prediction_hybrid(fixture_id: int) -> PredictionResponse:
    bracket_fixture = await _find_bracket_fixture(fixture_id)
    if not bracket_fixture:
        raise ResourceNotFoundError(f"Fixture {fixture_id} not found")

    if not bracket_fixture.home_resolved or not bracket_fixture.away_resolved:
        raise ResourceNotFoundError(
            f"Fixture {fixture_id} teams not yet determined — knockout slot pending"
        )

    summary = _bracket_to_summary(bracket_fixture)
    repo = await get_statsbomb_repository()

    home_stats = await compute_team_stats(repo, summary.home_team.name)
    away_stats = await compute_team_stats(repo, summary.away_team.name)
    home_h2h, h2h_count = h2h_win_rate(repo, summary.home_team.name, summary.away_team.name)
    away_h2h = (1.0 - home_h2h) if home_h2h is not None else None

    result = predict_match(
        _team_input(home_stats, home_h2h),
        _team_input(away_stats, away_h2h),
        h2h_match_count=h2h_count,
        team1_name=summary.home_team.name,
        team2_name=summary.away_team.name,
    )

    return PredictionResponse(
        fixture_id=fixture_id,
        home_win_probability=result.team1_win_probability,
        away_win_probability=result.team2_win_probability,
        draw_probability=result.draw_probability,
        home_expected_goals=result.team1_expected_goals,
        away_expected_goals=result.team2_expected_goals,
        confidence_score=result.confidence_score,
        prediction_label=result.prediction_label,
    )


# ---------------------------------------------------------------------------
# API-Football fallback
# ---------------------------------------------------------------------------

async def _list_teams_api_football() -> list[TeamSummary]:
    client = get_api_football_client()
    raw_teams = await client.get_teams(WC_LEAGUE_ID, WC_SEASON)
    return [transform_team_summary(entry) for entry in raw_teams]


async def _get_team_stats_api_football(team_id: int) -> TeamStatsResponse:
    client = get_api_football_client()
    raw_stats = await client.get_team_statistics(team_id, WC_LEAGUE_ID, WC_SEASON)
    if not raw_stats:
        raise ResourceNotFoundError(f"Team {team_id} not found")
    stats = transform_team_stats(raw_stats)
    if stats.team_id != team_id:
        stats = stats.model_copy(update={"team_id": team_id})
    return stats


async def _list_upcoming_api_football(limit: int) -> list[FixtureSummary]:
    client = get_api_football_client()
    raw_fixtures = await client.get_fixtures(WC_LEAGUE_ID, WC_SEASON)
    now = datetime.now(timezone.utc)
    upcoming: list[dict[str, Any]] = []
    for entry in raw_fixtures:
        fixture = entry["fixture"]
        kickoff = datetime.fromisoformat(fixture["date"].replace("Z", "+00:00"))
        if kickoff >= now and fixture["status"]["short"] in UPCOMING_STATUSES:
            upcoming.append(entry)
    upcoming.sort(key=lambda item: item["fixture"]["date"])
    return [transform_fixture(entry) for entry in upcoming[:limit]]


async def _get_fixture_detail_api_football(fixture_id: int) -> FixtureDetailResponse:
    client = get_api_football_client()
    raw_fixture = await client.get_fixture(fixture_id)
    if not raw_fixture:
        raise ResourceNotFoundError(f"Fixture {fixture_id} not found")
    summary = transform_fixture(raw_fixture)
    home_stats, away_stats = await asyncio.gather(
        _get_team_stats_api_football(summary.home_team.id),
        _get_team_stats_api_football(summary.away_team.id),
    )
    return FixtureDetailResponse(
        **summary.model_dump(),
        home_stats=home_stats,
        away_stats=away_stats,
    )


async def _get_prediction_api_football(fixture_id: int) -> PredictionResponse:
    client = get_api_football_client()
    raw_fixture = await client.get_fixture(fixture_id)
    if not raw_fixture:
        raise ResourceNotFoundError(f"Fixture {fixture_id} not found")
    summary = transform_fixture(raw_fixture)

    home_stats, away_stats, h2h_fixtures = await asyncio.gather(
        _get_team_stats_api_football(summary.home_team.id),
        _get_team_stats_api_football(summary.away_team.id),
        client.get_h2h(summary.home_team.id, summary.away_team.id),
    )

    home_h2h, h2h_count = _h2h_win_rate_api(h2h_fixtures, summary.home_team.id)
    away_h2h, _ = _h2h_win_rate_api(h2h_fixtures, summary.away_team.id)

    result = predict_match(
        _team_input(home_stats, home_h2h),
        _team_input(away_stats, away_h2h),
        h2h_match_count=h2h_count,
        team1_name=summary.home_team.name,
        team2_name=summary.away_team.name,
    )
    return PredictionResponse(
        fixture_id=fixture_id,
        home_win_probability=result.team1_win_probability,
        away_win_probability=result.team2_win_probability,
        draw_probability=result.draw_probability,
        home_expected_goals=result.team1_expected_goals,
        away_expected_goals=result.team2_expected_goals,
        confidence_score=result.confidence_score,
        prediction_label=result.prediction_label,
    )


def _h2h_win_rate_api(h2h_fixtures: list[dict[str, Any]], team_id: int) -> tuple[float | None, int]:
    wins = total = 0
    for entry in h2h_fixtures:
        status = entry["fixture"]["status"]["short"]
        if status not in {"FT", "AET", "PEN"}:
            continue
        home = entry["teams"]["home"]
        away = entry["teams"]["away"]
        if team_id not in {home["id"], away["id"]}:
            continue
        total += 1
        if home["id"] == team_id and home.get("winner") is True:
            wins += 1
        elif away["id"] == team_id and away.get("winner") is True:
            wins += 1
    if total == 0:
        return None, 0
    return wins / total, total
