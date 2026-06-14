"""Player and squad models."""

from enum import Enum

from pydantic import BaseModel, Field


class SquadCategory(str, Enum):
    """World Cup squad role grouping."""

    STARTING = "starting"
    SUBSTITUTE = "substitute"
    RESERVE = "reserve"
    INJURED = "injured"


class PlayerSummary(BaseModel):
    """A player on a national team squad."""

    id: int
    name: str
    number: int | None = None
    position: str | None = None
    age: int | None = None
    photo: str | None = None
    category: SquadCategory
    injury_reason: str | None = None


class TeamSquadResponse(BaseModel):
    """Full squad breakdown for a national team."""

    team_id: int
    team_name: str
    source: str = Field(description="espn, api_football, or statsbomb")
    is_live_lineup: bool = False
    live_minute: int | None = None
    live_fixture_id: int | None = None
    lineup_confirmed: bool = False
    all_players: list[PlayerSummary] = Field(default_factory=list)
    starting_xi: list[PlayerSummary] = Field(default_factory=list)
    substitutes: list[PlayerSummary] = Field(default_factory=list)
    reserves: list[PlayerSummary] = Field(default_factory=list)
    injured: list[PlayerSummary] = Field(default_factory=list)
