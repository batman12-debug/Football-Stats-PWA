"""Tests for StatsBomb possession calculation."""

import pytest

from app.services.data_sources.possession import possession_from_events, team_possession_in_match


def test_possession_from_events_splits_by_duration():
    events = [
        {
            "duration": 60.0,
            "possession_team": {"name": "Brazil"},
        },
        {
            "duration": 40.0,
            "possession_team": {"name": "Belgium"},
        },
        {
            "duration": 10.0,
            "possession_team": {"name": "Brazil"},
        },
        {"duration": 5.0},  # no possession_team — ignored
    ]

    result = possession_from_events(events)

    assert result["Brazil"] == pytest.approx(63.64, abs=0.01)
    assert result["Belgium"] == pytest.approx(36.36, abs=0.01)


def test_possession_empty_when_no_durations():
    assert possession_from_events([{"type": {"name": "Pass"}}]) == {}


def test_team_possession_in_match_normalizes_names():
    mapping = {"United States": 55.0, "England": 45.0}
    assert team_possession_in_match(mapping, "USA") == 55.0
