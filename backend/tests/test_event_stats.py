"""Tests for event-based live match statistics."""

from app.services.data_sources.event_stats import aggregate_match_stats


def test_aggregate_match_stats_from_events():
    events = [
        {
            "minute": 10,
            "type": {"name": "Shot"},
            "team": {"name": "Brazil"},
            "shot": {"outcome": {"name": "Goal"}},
            "duration": 2.0,
            "possession_team": {"name": "Brazil"},
        },
        {
            "minute": 12,
            "type": {"name": "Shot"},
            "team": {"name": "Belgium"},
            "shot": {"outcome": {"name": "Off T"}},
            "duration": 1.0,
            "possession_team": {"name": "Belgium"},
        },
        {
            "minute": 15,
            "type": {"name": "Pass"},
            "team": {"name": "Brazil"},
            "pass": {},
            "duration": 1.0,
            "possession_team": {"name": "Brazil"},
        },
        {
            "minute": 16,
            "type": {"name": "Pass"},
            "team": {"name": "Brazil"},
            "pass": {"outcome": {"name": "Incomplete"}},
            "duration": 1.0,
            "possession_team": {"name": "Brazil"},
        },
        {
            "minute": 20,
            "type": {"name": "Foul Committed"},
            "team": {"name": "Belgium"},
            "foul_committed": {"card": {"name": "Yellow Card"}},
        },
    ]

    stats = aggregate_match_stats(events, "Brazil", "Belgium", max_minute=25)

    assert stats.home.shots == 1
    assert stats.home.shots_on_target == 1
    assert stats.away.shots == 1
    assert stats.home.passes == 2
    assert stats.home.passes_completed == 1
    assert stats.away.yellow_cards == 1
