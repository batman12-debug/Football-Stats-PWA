"""Unit tests for the weighted prediction engine."""

import pytest

from app.services.prediction_engine import TeamInput, predict_match


def _balanced_team(**overrides) -> TeamInput:
    defaults = {
        "recent_form": 0.5,
        "avg_goals_scored": 1.5,
        "avg_goals_conceded": 1.5,
        "h2h_win_rate": 0.5,
        "possession_avg": 50.0,
    }
    defaults.update(overrides)
    return TeamInput(**defaults)


def test_equal_teams_near_thirds_each():
    team1 = _balanced_team()
    team2 = _balanced_team()

    result = predict_match(team1, team2, h2h_match_count=5)

    assert abs(result.team1_win_probability - 1 / 3) < 0.05
    assert abs(result.team2_win_probability - 1 / 3) < 0.05
    assert abs(result.draw_probability - 1 / 3) < 0.05
    assert pytest.approx(
        result.team1_win_probability
        + result.team2_win_probability
        + result.draw_probability,
        abs=1e-9,
    ) == 1.0


def test_dominant_team_above_sixty_percent():
    dominant = _balanced_team(
        recent_form=0.9,
        avg_goals_scored=2.7,
        avg_goals_conceded=0.6,
        h2h_win_rate=0.85,
        possession_avg=62.0,
    )
    weak = _balanced_team(
        recent_form=0.2,
        avg_goals_scored=0.6,
        avg_goals_conceded=2.4,
        h2h_win_rate=0.15,
        possession_avg=38.0,
    )

    result = predict_match(dominant, weak, h2h_match_count=8, team1_name="Brazil")

    assert result.team1_win_probability > 0.60
    assert result.prediction_label == "Brazil likely wins"
    assert result.team1_expected_goals > result.team2_expected_goals


def test_no_h2h_data_falls_back_to_form_only():
    strong_form = _balanced_team(recent_form=0.8, h2h_win_rate=None)
    weak_form = _balanced_team(recent_form=0.3, h2h_win_rate=None)

    result = predict_match(strong_form, weak_form, h2h_match_count=0)

    assert result.team1_win_probability > result.team2_win_probability
    assert result.confidence_score == 0.35
    assert pytest.approx(
        result.team1_win_probability
        + result.team2_win_probability
        + result.draw_probability,
        abs=1e-9,
    ) == 1.0


def test_expected_goals_use_possession_multiplier():
    team = _balanced_team(avg_goals_scored=2.0, possession_avg=60.0)

    result = predict_match(team, _balanced_team())

    assert result.team1_expected_goals == pytest.approx(2.4)
