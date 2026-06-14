"""Parse scores and goal scorers from OpenFootball worldcup.json match records."""

from __future__ import annotations

from typing import Any


def parse_full_time_score(raw: dict[str, Any]) -> tuple[int | None, int | None]:
    """Extract full-time home/away goals from an OpenFootball match dict."""
    if raw.get("score1") is not None and raw.get("score2") is not None:
        return int(raw["score1"]), int(raw["score2"])

    score = raw.get("score")
    if isinstance(score, dict):
        ft = score.get("ft")
        if isinstance(ft, (list, tuple)) and len(ft) >= 2:
            return int(ft[0]), int(ft[1])

    return None, None


def parse_goal_scorers(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """Build normalized goal-scorer rows from goals1 / goals2 arrays."""
    scorers: list[dict[str, Any]] = []
    home_team = raw.get("team1", "Home")
    away_team = raw.get("team2", "Away")

    for entry in raw.get("goals1") or []:
        if not isinstance(entry, dict):
            continue
        name = (entry.get("name") or "").strip()
        if not name:
            continue
        scorers.append(
            {
                "player_name": name,
                "minute": str(entry.get("minute", "")),
                "team": home_team,
                "is_own_goal": "own goal" in name.lower(),
            }
        )

    for entry in raw.get("goals2") or []:
        if not isinstance(entry, dict):
            continue
        name = (entry.get("name") or "").strip()
        if not name:
            continue
        scorers.append(
            {
                "player_name": name,
                "minute": str(entry.get("minute", "")),
                "team": away_team,
                "is_own_goal": "own goal" in name.lower(),
            }
        )

    scorers.sort(key=lambda g: _minute_sort_key(g.get("minute", "")))
    return scorers


def _minute_sort_key(minute: str) -> tuple[int, int]:
    digits = "".join(ch for ch in minute if ch.isdigit())
    base = int(digits) if digits else 999
    extra = 1 if "+" in minute else 0
    return (base, extra)


def match_has_result(raw: dict[str, Any]) -> bool:
    home, away = parse_full_time_score(raw)
    return home is not None and away is not None
