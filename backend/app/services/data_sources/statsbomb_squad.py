"""Build accurate national-team squads from StatsBomb World Cup data."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.services.data_sources.statsbomb import StatsBombError, get_statsbomb_client, get_statsbomb_repository
from app.services.data_sources.team_names import normalize_team_name

logger = logging.getLogger(__name__)

SQUAD_SIZE = 26
MATCHDAY_BENCH = 12


@dataclass
class RawSquadPlayer:
    id: int
    name: str
    number: int | None
    position: str | None
    photo: str | None = None


@dataclass
class LineupRoles:
    starters: list[RawSquadPlayer] = field(default_factory=list)
    bench: list[RawSquadPlayer] = field(default_factory=list)
    on_field: list[RawSquadPlayer] = field(default_factory=list)
    is_live: bool = False
    live_minute: int | None = None
    live_fixture_id: int | None = None


def _display_name(player: dict[str, Any]) -> str:
    nickname = (player.get("player_nickname") or "").strip()
    if nickname:
        return nickname
    full = (player.get("player_name") or "").strip()
    parts = full.split()
    if len(parts) <= 2:
        return full
    return f"{parts[0]} {parts[-1]}"


def _primary_position(player: dict[str, Any]) -> str | None:
    positions = player.get("positions") or []
    if not positions:
        return None
    return str(positions[0].get("position") or "")


def _is_starter_at_kickoff(player: dict[str, Any]) -> bool:
    for pos in player.get("positions") or []:
        if str(pos.get("from", "")).startswith("00:") and pos.get("start_reason") == "Starting XI":
            return True
    return False


def _raw_from_lineup_player(player: dict[str, Any]) -> RawSquadPlayer:
    return RawSquadPlayer(
        id=int(player["player_id"]),
        name=_display_name(player),
        number=player.get("jersey_number"),
        position=_primary_position(player),
    )


async def collect_team_squad_players(team_name: str) -> list[RawSquadPlayer]:
    """All unique players from World Cup matches, preferring recent squads."""
    repo = await get_statsbomb_repository()
    client = get_statsbomb_client()
    history = repo.team_match_history(team_name)
    team_key = normalize_team_name(team_name)

    ordered: list[int] = []
    by_id: dict[int, RawSquadPlayer] = {}

    for match in history:
        try:
            lineups = await client.get_lineups(match["match_id"])
        except StatsBombError:
            continue

        for team_lineup in lineups:
            if normalize_team_name(team_lineup.get("team_name", "")) != team_key:
                continue

            for player in team_lineup.get("lineup", []):
                pid = int(player["player_id"])
                if pid in by_id:
                    continue
                ordered.append(pid)
                by_id[pid] = _raw_from_lineup_player(player)

    return [by_id[pid] for pid in ordered[:SQUAD_SIZE]]


async def latest_match_roles(team_name: str) -> tuple[list[RawSquadPlayer], list[RawSquadPlayer]]:
    """Starting XI and bench from the most recent World Cup match."""
    repo = await get_statsbomb_repository()
    client = get_statsbomb_client()
    history = repo.team_match_history(team_name)
    team_key = normalize_team_name(team_name)

    for match in history:
        try:
            lineups = await client.get_lineups(match["match_id"])
        except StatsBombError:
            continue

        for team_lineup in lineups:
            if normalize_team_name(team_lineup.get("team_name", "")) != team_key:
                continue

            starters: list[RawSquadPlayer] = []
            bench: list[RawSquadPlayer] = []
            for player in team_lineup.get("lineup", []):
                raw = _raw_from_lineup_player(player)
                if _is_starter_at_kickoff(player):
                    starters.append(raw)
                else:
                    bench.append(raw)

            if starters:
                return starters[:11], bench

    return [], []


def _parse_event_minute(event: dict[str, Any]) -> float | None:
    minute = event.get("minute")
    second = event.get("second") or 0
    if minute is None:
        return None
    try:
        return float(minute) + float(second) / 60.0
    except (TypeError, ValueError):
        return None


async def on_field_at_minute(
    team_name: str,
    match_id: int,
    minute: int,
) -> list[RawSquadPlayer]:
    """Players on the pitch at a given minute (after subs)."""
    client = get_statsbomb_client()
    team_key = normalize_team_name(team_name)

    try:
        lineups = await client.get_lineups(match_id)
        events = await client.get_events(match_id)
    except StatsBombError:
        return []

    lineup_players: dict[int, dict[str, Any]] = {}
    starters: list[int] = []

    for team_lineup in lineups:
        if normalize_team_name(team_lineup.get("team_name", "")) != team_key:
            continue
        for player in team_lineup.get("lineup", []):
            pid = int(player["player_id"])
            lineup_players[pid] = player
            if _is_starter_at_kickoff(player):
                starters.append(pid)

    on_field = set(starters)

    for event in events:
        type_name = (event.get("type") or {}).get("name")
        if type_name != "Substitution":
            continue
        if normalize_team_name((event.get("team") or {}).get("name", "")) != team_key:
            continue

        when = _parse_event_minute(event)
        if when is None or when > minute:
            continue

        sub = event.get("substitution") or {}
        out_player = (event.get("player") or {}).get("id")
        in_player = (sub.get("replacement") or {}).get("id")
        if out_player in on_field:
            on_field.discard(out_player)
        if in_player is not None:
            on_field.add(int(in_player))

    result = [
        _raw_from_lineup_player(lineup_players[pid])
        for pid in on_field
        if pid in lineup_players
    ]
    result.sort(key=lambda p: (p.number or 99, p.name))
    return result[:11]
