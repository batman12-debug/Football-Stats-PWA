"""Team data models."""

from pydantic import BaseModel, Field


class TeamSummary(BaseModel):
    """Compact team representation for lists and fixtures."""

    id: int
    name: str
    code: str | None = None
    logo: str | None = None


class TeamStatsResponse(BaseModel):
    """Team statistics exposed by the API."""

    team_id: int
    name: str
    code: str | None = None
    logo: str | None = None
    recent_form: float = Field(ge=0.0, le=1.0)
    avg_goals_scored: float = Field(ge=0.0)
    avg_goals_conceded: float = Field(ge=0.0)
    possession_avg: float = Field(ge=0.0, le=100.0)
    form_string: str | None = None
    matches_played: int = Field(ge=0)
