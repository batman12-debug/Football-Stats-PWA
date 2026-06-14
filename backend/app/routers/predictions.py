"""Predictions API routes."""

import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path

from app.models.prediction import PredictionResponse
from app.security.errors import NOT_FOUND, SERVICE_UNAVAILABLE
from app.services.api_football import APIFootballError
from app.services.football_data import FootballDataError, ResourceNotFoundError, get_prediction

logger = logging.getLogger(__name__)
router = APIRouter()

FixtureId = Path(..., ge=1, le=99_999_999, description="OpenFootball fixture ID")


FixtureIdPath = Annotated[int, FixtureId]


@router.get("/{fixture_id}", response_model=PredictionResponse)
async def get_match_prediction(fixture_id: FixtureIdPath) -> PredictionResponse:
    """Generate a prediction for the given fixture."""
    try:
        return await get_prediction(fixture_id)
    except ResourceNotFoundError as exc:
        logger.info("Prediction not found for fixture %s: %s", fixture_id, exc)
        raise HTTPException(status_code=404, detail=NOT_FOUND) from exc
    except (APIFootballError, FootballDataError) as exc:
        logger.error("Failed to generate prediction for fixture %s: %s", fixture_id, exc)
        raise HTTPException(status_code=503, detail=SERVICE_UNAVAILABLE) from exc
