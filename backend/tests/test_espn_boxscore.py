"""Tests for ESPN live boxscore parsing."""

from app.services.data_sources.espn_wc import parse_espn_team_box_stats


def test_parse_espn_team_box_stats_maps_fouls_and_cards():
    statistics = [
        {"name": "foulsCommitted", "displayValue": "8"},
        {"name": "yellowCards", "displayValue": "2"},
        {"name": "redCards", "displayValue": "0"},
        {"name": "totalShots", "displayValue": "6"},
        {"name": "shotsOnTarget", "displayValue": "2"},
        {"name": "possessionPct", "displayValue": "54.1"},
        {"name": "totalPasses", "displayValue": "257"},
        {"name": "accuratePasses", "displayValue": "224"},
        {"name": "passPct", "displayValue": "0.9"},
        {"name": "wonCorners", "displayValue": "2"},
        {"name": "offsides", "displayValue": "0"},
    ]

    stats = parse_espn_team_box_stats(statistics)

    assert stats.fouls == 8
    assert stats.yellow_cards == 2
    assert stats.red_cards == 0
    assert stats.shots == 6
    assert stats.passes == 257
    assert stats.pass_accuracy == 90.0
    assert stats.possession == 54.1
