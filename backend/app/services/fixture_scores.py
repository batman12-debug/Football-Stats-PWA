"""Resolve fixture status and scores from OpenFootball + ESPN (Tier 1 + Tier 2)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services.data_sources.espn_wc import (
    EspnMatchSnapshot,
    build_espn_wc_index,
    lookup_espn_match,
)
from app.services.data_sources.results_store import get_result

LIVE_STATUSES = frozenset({"LIVE", "1H", "2H", "HT", "ET", "BT", "P", "INT"})
MATCH_DURATION = timedelta(minutes=105)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def resolve_match_status(
    kickoff: datetime,
    stored_status: str,
    fixture_id: int,
) -> str:
    """Derive display status from stored state and kickoff time."""
    if stored_status in {"FT", "AET", "PEN"}:
        return stored_status

    result = await get_result(fixture_id)
    if result is not None:
        return "FT"

    now = _utcnow()
    if kickoff.tzinfo is None:
        kickoff = kickoff.replace(tzinfo=timezone.utc)

    if now < kickoff:
        return stored_status if stored_status != "NS" else "NS"

    if now < kickoff + MATCH_DURATION:
        return "LIVE"

    return stored_status if stored_status not in {"NS", "TBD"} else "FT"


def _apply_espn_snapshot(
    snapshot: EspnMatchSnapshot,
    *,
    home_name: str,
    away_name: str,
) -> tuple[str, int, int, int | None]:
    if snapshot.is_live or snapshot.status in LIVE_STATUSES:
        return snapshot.status, snapshot.home_goals, snapshot.away_goals, snapshot.minute
    if snapshot.status == "FT":
        return "FT", snapshot.home_goals, snapshot.away_goals, None
    return snapshot.status, snapshot.home_goals, snapshot.away_goals, snapshot.minute


async def resolve_fixture_display(
    *,
    fixture_id: int,
    kickoff: datetime,
    stored_status: str,
    stored_home_goals: int | None,
    stored_away_goals: int | None,
    home_name: str,
    away_name: str,
    espn_index: dict | None = None,
) -> tuple[str, int | None, int | None, int | None]:
    """Return display status, goals, and live minute using real data sources only."""
    if kickoff.tzinfo is None:
        kickoff = kickoff.replace(tzinfo=timezone.utc)

    result = await get_result(fixture_id)
    if result is not None:
        return "FT", result["home_goals"], result["away_goals"], None

    index = espn_index
    if index is None:
        index = await build_espn_wc_index()

    espn = lookup_espn_match(
        index,
        home_name=home_name,
        away_name=away_name,
        kickoff=kickoff,
    )

    if espn is not None and (espn.is_live or espn.status in LIVE_STATUSES):
        status, hg, ag, minute = _apply_espn_snapshot(
            espn, home_name=home_name, away_name=away_name
        )
        return status, hg, ag, minute

    if stored_home_goals is not None and stored_away_goals is not None:
        status = stored_status if stored_status in {"FT", "AET", "PEN"} else "FT"
        return status, stored_home_goals, stored_away_goals, None

    if espn is not None and espn.status == "FT":
        return "FT", espn.home_goals, espn.away_goals, None

    status = await resolve_match_status(kickoff, stored_status, fixture_id)
    now = _utcnow()

    if now < kickoff:
        return stored_status if stored_status != "NS" else "NS", None, None, None

    if status == "LIVE" or status in LIVE_STATUSES:
        if espn is not None:
            return _apply_espn_snapshot(espn, home_name=home_name, away_name=away_name)
        return status, None, None, _elapsed_minute(kickoff)

    if status in {"FT", "AET", "PEN"}:
        return status, stored_home_goals, stored_away_goals, None

    return status, stored_home_goals, stored_away_goals, None


def _elapsed_minute(kickoff: datetime, now: datetime | None = None) -> int:
    now = now or _utcnow()
    if kickoff.tzinfo is None:
        kickoff = kickoff.replace(tzinfo=timezone.utc)
    elapsed = (now - kickoff).total_seconds() / 60.0
    return max(0, min(90, int(elapsed)))
