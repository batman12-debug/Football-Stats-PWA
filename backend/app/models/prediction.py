"""Prediction data models."""

from pydantic import BaseModel, Field


class PredictionResponse(BaseModel):
    """Match outcome prediction returned by the API."""

    fixture_id: int
    home_win_probability: float = Field(ge=0.0, le=1.0)
    away_win_probability: float = Field(ge=0.0, le=1.0)
    draw_probability: float = Field(ge=0.0, le=1.0)
    home_expected_goals: float = Field(ge=0.0)
    away_expected_goals: float = Field(ge=0.0)
    confidence_score: float = Field(ge=0.0, le=1.0)
    prediction_label: str
