"""Teams API routes."""

import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path

from app.models.player import TeamSquadResponse
from app.models.team import TeamStatsResponse, TeamSummary
from app.security.errors import NOT_FOUND, SERVICE_UNAVAILABLE
from app.services.api_football import APIFootballError
from app.services.football_data import (
    FootballDataError,
    ResourceNotFoundError,
    get_team_squad,
    get_team_stats,
    list_teams,
)

logger = logging.getLogger(__name__)
router = APIRouter()

TeamId = Path(..., ge=1, le=9_999_999_999, description="Team ID")


@router.get("", response_model=list[TeamSummary])
async def list_world_cup_teams() -> list[TeamSummary]:
    """List all World Cup 2026 teams."""
    try:
        return await list_teams()
    except (APIFootballError, FootballDataError) as exc:
        logger.error("Failed to list teams: %s", exc)
        raise HTTPException(status_code=503, detail=SERVICE_UNAVAILABLE) from exc


TeamIdPath = Annotated[int, TeamId]


@router.get("/{team_id}/squad", response_model=TeamSquadResponse)
async def get_team_squad_roster(team_id: TeamIdPath) -> TeamSquadResponse:
    """Return squad roster grouped by role."""
    try:
        return await get_team_squad(team_id)
    except ResourceNotFoundError as exc:
        logger.info("Squad not found for team %s: %s", team_id, exc)
        raise HTTPException(status_code=404, detail=NOT_FOUND) from exc
    except ValueError as exc:
        logger.info("Squad unavailable for team %s: %s", team_id, exc)
        raise HTTPException(status_code=404, detail=NOT_FOUND) from exc
    except (APIFootballError, FootballDataError) as exc:
        logger.error("Failed to fetch squad for team %s: %s", team_id, exc)
        raise HTTPException(status_code=503, detail=SERVICE_UNAVAILABLE) from exc


@router.get("/{team_id}/stats", response_model=TeamStatsResponse)
async def get_team_statistics(team_id: TeamIdPath) -> TeamStatsResponse:
    """Return full statistics for a single team."""
    try:
        return await get_team_stats(team_id)
    except ResourceNotFoundError as exc:
        logger.info("Stats not found for team %s: %s", team_id, exc)
        raise HTTPException(status_code=404, detail=NOT_FOUND) from exc
    except (APIFootballError, FootballDataError) as exc:
        logger.error("Failed to fetch stats for team %s: %s", team_id, exc)
        raise HTTPException(status_code=503, detail=SERVICE_UNAVAILABLE) from exc
