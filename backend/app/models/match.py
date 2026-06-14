"""Match data models."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.team import TeamStatsResponse, TeamSummary


class BracketTeamSummary(TeamSummary):
    """Team in bracket view — may be a resolved name or placeholder label."""

    is_placeholder: bool = False
    raw_name: str | None = None


class GroupStandingRow(BaseModel):
    team: str
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0
    points: int = 0
    goal_diff: int = 0


class GoalScorer(BaseModel):
    player_name: str
    minute: str
    team: str
    is_own_goal: bool = False


class BracketFixtureSummary(BaseModel):
    id: int
    date: datetime
    status: str
    stage: str
    round_name: str
    group: str | None = None
    match_number: int | None = None
    home_team: BracketTeamSummary
    away_team: BracketTeamSummary
    home_goals: int | None = None
    away_goals: int | None = None
    venue: str | None = None
    home_resolved: bool = True
    away_resolved: bool = True
    goal_scorers: list[GoalScorer] = Field(default_factory=list)


class TournamentGroupSection(BaseModel):
    group: str
    standings: list[GroupStandingRow] = Field(default_factory=list)
    fixtures: list[BracketFixtureSummary]


class TournamentStageSection(BaseModel):
    stage: str
    label: str
    groups: list[TournamentGroupSection] | None = None
    fixtures: list[BracketFixtureSummary] = Field(default_factory=list)


class TournamentBracketResponse(BaseModel):
    tournament: str
    stages: list[TournamentStageSection]


class MatchResultUpdate(BaseModel):
    home_goals: int = Field(ge=0)
    away_goals: int = Field(ge=0)


class FixtureSummary(BaseModel):
    """Upcoming or completed fixture."""

    id: int
    date: datetime
    status: str
    home_team: TeamSummary
    away_team: TeamSummary
    home_goals: int | None = None
    away_goals: int | None = None
    venue: str | None = None
    goal_scorers: list[GoalScorer] = Field(default_factory=list)


class FixtureDetailResponse(FixtureSummary):
    """Fixture with both teams' statistics."""

    home_stats: TeamStatsResponse
    away_stats: TeamStatsResponse


class LiveTeamStats(BaseModel):
    shots: int = 0
    shots_on_target: int = 0
    possession: float = 50.0
    passes: int = 0
    pass_accuracy: float = 0.0
    fouls: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    offsides: int = 0
    corners: int = 0


class LiveMatchStatsResponse(BaseModel):
    fixture_id: int
    is_live: bool
    status: str
    minute: int = 0
    home_team: str
    away_team: str
    home_goals: int | None = None
    away_goals: int | None = None
    home: LiveTeamStats
    away: LiveTeamStats
