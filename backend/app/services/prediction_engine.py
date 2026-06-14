"""Match prediction engine — weighted statistical model."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TeamInput:
    """Per-team statistics used by the prediction model."""

    recent_form: float
    avg_goals_scored: float
    avg_goals_conceded: float
    h2h_win_rate: float | None
    possession_avg: float


@dataclass(frozen=True)
class PredictionResult:
    """Predicted match outcome."""

    team1_win_probability: float
    team2_win_probability: float
    draw_probability: float
    team1_expected_goals: float
    team2_expected_goals: float
    confidence_score: float
    prediction_label: str


_WEIGHTS_WITH_H2H = {
    "h2h": 0.30,
    "form": 0.25,
    "goals_scored": 0.20,
    "goals_conceded": 0.15,
    "possession": 0.10,
}

_WEIGHTS_WITHOUT_H2H = {
    "form": 0.25 / 0.70,
    "goals_scored": 0.20 / 0.70,
    "goals_conceded": 0.15 / 0.70,
    "possession": 0.10 / 0.70,
}


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(value, upper))


def _compute_raw_score(team: TeamInput) -> float:
    """Return a single-team strength score in roughly the 0.0–1.0 range."""
    form = _clamp(team.recent_form, 0.0, 1.0)
    goals_scored = _clamp(team.avg_goals_scored / 3.0, 0.0, 1.0)
    goals_conceded = _clamp(1.0 - team.avg_goals_conceded / 3.0, 0.0, 1.0)
    possession = _clamp(team.possession_avg / 100.0, 0.0, 1.0)

    if team.h2h_win_rate is not None:
        h2h = _clamp(team.h2h_win_rate, 0.0, 1.0)
        weights = _WEIGHTS_WITH_H2H
        return (
            weights["h2h"] * h2h
            + weights["form"] * form
            + weights["goals_scored"] * goals_scored
            + weights["goals_conceded"] * goals_conceded
            + weights["possession"] * possession
        )

    weights = _WEIGHTS_WITHOUT_H2H
    return (
        weights["form"] * form
        + weights["goals_scored"] * goals_scored
        + weights["goals_conceded"] * goals_conceded
        + weights["possession"] * possession
    )


def _expected_goals(team: TeamInput) -> float:
    possession_multiplier = _clamp(team.possession_avg / 50.0, 0.0, 2.0)
    return max(0.0, team.avg_goals_scored * possession_multiplier)


def _normalize_probabilities(raw1: float, raw2: float) -> tuple[float, float, float]:
    """Convert raw scores into win/draw/win probabilities summing to 1.0."""
    raw1 = max(raw1, 0.0)
    raw2 = max(raw2, 0.0)
    draw_raw = min(raw1, raw2) * (1.0 - abs(raw1 - raw2))

    total = raw1 + raw2 + draw_raw
    if total == 0.0:
        return 1 / 3, 1 / 3, 1 / 3

    return raw1 / total, raw2 / total, draw_raw / total


def _confidence_score(team1: TeamInput, team2: TeamInput, h2h_match_count: int) -> float:
    has_h2h = team1.h2h_win_rate is not None or team2.h2h_win_rate is not None
    if not has_h2h or h2h_match_count <= 0:
        return 0.35
    return _clamp(h2h_match_count / 5.0, 0.0, 1.0)


def _prediction_label(
    team1_win: float,
    team2_win: float,
    draw: float,
    team1_name: str,
    team2_name: str,
) -> str:
    if team1_win > 0.55:
        return f"{team1_name} likely wins"
    if team2_win > 0.55:
        return f"{team2_name} likely wins"
    if draw > 0.35:
        return "Draw likely"
    return "Toss-up"


def predict_match(
    team1: TeamInput,
    team2: TeamInput,
    *,
    h2h_match_count: int = 0,
    team1_name: str = "Team 1",
    team2_name: str = "Team 2",
) -> PredictionResult:
    """Generate win/draw/loss probabilities and expected goals for a fixture."""
    raw1 = _compute_raw_score(team1)
    raw2 = _compute_raw_score(team2)
    team1_win, team2_win, draw = _normalize_probabilities(raw1, raw2)

    return PredictionResult(
        team1_win_probability=team1_win,
        team2_win_probability=team2_win,
        draw_probability=draw,
        team1_expected_goals=_expected_goals(team1),
        team2_expected_goals=_expected_goals(team2),
        confidence_score=_confidence_score(team1, team2, h2h_match_count),
        prediction_label=_prediction_label(
            team1_win, team2_win, draw, team1_name, team2_name
        ),
    )
