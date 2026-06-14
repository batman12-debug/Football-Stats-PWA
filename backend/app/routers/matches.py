"""Matches API routes."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from app.deps.admin_auth import require_admin_api_key
from app.models.match import (
    FixtureDetailResponse,
    FixtureSummary,
    LiveMatchStatsResponse,
    MatchResultUpdate,
    TournamentBracketResponse,
)
from app.security.errors import NOT_FOUND, SERVICE_UNAVAILABLE
from app.services.api_football import APIFootballError
from app.services.football_data import (
    FootballDataError,
    ResourceNotFoundError,
    get_fixture_detail,
    get_tournament_bracket,
    list_upcoming_fixtures,
    record_match_result,
)
from app.services.match_live import get_live_match_stats

logger = logging.getLogger(__name__)
router = APIRouter()

FixtureId = Path(..., ge=1, le=99_999_999, description="OpenFootball fixture ID")


@router.get("/bracket", response_model=TournamentBracketResponse)
async def get_bracket() -> TournamentBracketResponse:
    """Return full tournament bracket grouped by stage."""
    try:
        return await get_tournament_bracket()
    except (APIFootballError, FootballDataError) as exc:
        logger.error("Failed to build tournament bracket: %s", exc)
        raise HTTPException(status_code=503, detail=SERVICE_UNAVAILABLE) from exc


@router.get("/upcoming", response_model=list[FixtureSummary])
async def get_upcoming_matches() -> list[FixtureSummary]:
    """Return the next 10 upcoming fixtures with known teams."""
    try:
        return await list_upcoming_fixtures(limit=10)
    except (APIFootballError, FootballDataError) as exc:
        logger.error("Failed to list upcoming fixtures: %s", exc)
        raise HTTPException(status_code=503, detail=SERVICE_UNAVAILABLE) from exc


FixtureIdPath = Annotated[int, FixtureId]


@router.post("/{fixture_id}/result")
async def submit_match_result(
    body: MatchResultUpdate,
    fixture_id: FixtureIdPath,
    _: None = Depends(require_admin_api_key),
) -> dict[str, str]:
    """Record a match result — requires X-Admin-Key header."""
    try:
        await record_match_result(fixture_id, body.home_goals, body.away_goals)
        return {"status": "ok", "message": "Result saved. Bracket will reflect on refresh."}
    except FootballDataError as exc:
        logger.error("Failed to record result for fixture %s: %s", fixture_id, exc)
        raise HTTPException(status_code=503, detail=SERVICE_UNAVAILABLE) from exc


@router.get("/{fixture_id}/live-stats", response_model=LiveMatchStatsResponse)
async def get_match_live_stats(fixture_id: FixtureIdPath) -> LiveMatchStatsResponse:
    """Return real-time match statistics for in-progress fixtures."""
    try:
        return await get_live_match_stats(fixture_id)
    except ResourceNotFoundError as exc:
        logger.info("Live stats not found for fixture %s: %s", fixture_id, exc)
        raise HTTPException(status_code=404, detail=NOT_FOUND) from exc
    except (APIFootballError, FootballDataError) as exc:
        logger.error("Failed to fetch live stats for fixture %s: %s", fixture_id, exc)
        raise HTTPException(status_code=503, detail=SERVICE_UNAVAILABLE) from exc


@router.get("/{fixture_id}", response_model=FixtureDetailResponse)
async def get_match_detail(fixture_id: FixtureIdPath) -> FixtureDetailResponse:
    """Return match detail with both teams' statistics."""
    try:
        return await get_fixture_detail(fixture_id)
    except ResourceNotFoundError as exc:
        logger.info("Fixture not found %s: %s", fixture_id, exc)
        raise HTTPException(status_code=404, detail=NOT_FOUND) from exc
    except (APIFootballError, FootballDataError) as exc:
        logger.error("Failed to fetch fixture %s: %s", fixture_id, exc)
        raise HTTPException(status_code=503, detail=SERVICE_UNAVAILABLE) from exc
