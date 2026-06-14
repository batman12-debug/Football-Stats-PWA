"""Build World Cup squad rosters with role groupings."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.config import settings
from app.models.player import PlayerSummary, SquadCategory, TeamSquadResponse
from app.services.api_football import APIFootballError, get_api_football_client
from app.services.data_sources.api_team_ids import resolve_api_football_team_id
from app.services.data_sources.espn_wc import (
    EspnLineupPlayer,
    EspnMatchSnapshot,
    build_espn_wc_index,
    fetch_espn_team_lineup,
    lookup_espn_match,
)
from app.services.data_sources.statsbomb_squad import (
    MATCHDAY_BENCH,
    RawSquadPlayer,
    collect_team_squad_players,
)
from app.services.data_sources.thesportsdb import get_thesportsdb_client
from app.services.data_sources.team_names import normalize_team_name, stable_team_id
from app.services.fixture_scores import LIVE_STATUSES

logger = logging.getLogger(__name__)


def _position_bucket(position: str | None) -> str:
    if not position:
        return "midfielder"
    lower = position.lower()
    if "goal" in lower:
        return "goalkeeper"
    if "def" in lower or "back" in lower:
        return "defender"
    if "mid" in lower:
        return "midfielder"
    if "att" in lower or "forw" in lower or "strik" in lower or "wing" in lower:
        return "attacker"
    return "midfielder"


def _person_key(name: str) -> str:
    return normalize_team_name(name)


def _player_id_from_name(name: str) -> int:
    return 9_000_000 + (stable_team_id(name) % 1_000_000)


def _merge_espn_players(
    espn_players: tuple[EspnLineupPlayer, ...] | list[EspnLineupPlayer],
    squad: list[RawSquadPlayer],
) -> list[RawSquadPlayer]:
    """Map ESPN lineup names onto the squad roster, creating rows when needed."""
    by_exact: dict[str, RawSquadPlayer] = {_person_key(p.name): p for p in squad}
    by_last: dict[str, RawSquadPlayer] = {}
    for player in squad:
        parts = player.name.split()
        if parts:
            by_last[parts[-1].lower()] = player

    merged: list[RawSquadPlayer] = []
    for espn_player in espn_players:
        exact = by_exact.get(_person_key(espn_player.name))
        if exact:
            merged.append(
                RawSquadPlayer(
                    id=exact.id,
                    name=exact.name,
                    number=espn_player.number or exact.number,
                    position=espn_player.position or exact.position,
                    photo=exact.photo,
                )
            )
            continue

        last = espn_player.name.split()[-1].lower() if espn_player.name.split() else ""
        fuzzy = by_last.get(last)
        if fuzzy:
            merged.append(
                RawSquadPlayer(
                    id=fuzzy.id,
                    name=fuzzy.name,
                    number=espn_player.number or fuzzy.number,
                    position=espn_player.position or fuzzy.position,
                    photo=fuzzy.photo,
                )
            )
            continue

        merged.append(
            RawSquadPlayer(
                id=_player_id_from_name(espn_player.name),
                name=espn_player.name,
                number=espn_player.number,
                position=espn_player.position,
            )
        )

    return merged


def _to_summary(player: RawSquadPlayer, category: SquadCategory, *, injury_reason: str | None = None) -> PlayerSummary:
    return PlayerSummary(
        id=player.id,
        name=player.name,
        number=player.number,
        position=player.position,
        age=None,
        photo=player.photo,
        category=category,
        injury_reason=injury_reason,
    )


async def _enrich_photos(players: list[RawSquadPlayer], team_name: str) -> None:
    """Attach headshots from TheSportsDB where missing."""
    client = get_thesportsdb_client()
    missing = [p for p in players if not p.photo]

    async def attach(player: RawSquadPlayer) -> None:
        photo = await client.search_player_photo(player.name, team_name)
        if photo:
            player.photo = photo

    batch_size = 4
    for index in range(0, len(missing), batch_size):
        batch = missing[index : index + batch_size]
        await asyncio.gather(*(attach(player) for player in batch))


async def _find_espn_fixture_for_team(
    team_name: str,
) -> tuple[EspnMatchSnapshot, int] | None:
    """Best ESPN match for lineup lookup: live first, then most recent. Returns (snapshot, fixture_id)."""
    from app.services.football_data import get_tournament_bracket

    team_key = normalize_team_name(team_name)
    bracket = await get_tournament_bracket()
    espn_index = await build_espn_wc_index()

    candidates: list[tuple[int, int, EspnMatchSnapshot]] = []

    for stage in bracket.stages:
        fixture_groups: list[Any] = []
        if stage.groups:
            for group in stage.groups:
                fixture_groups.extend(group.fixtures)
        fixture_groups.extend(stage.fixtures)

        for fixture in fixture_groups:
            home_key = normalize_team_name(fixture.home_team.name)
            away_key = normalize_team_name(fixture.away_team.name)
            if team_key not in {home_key, away_key}:
                continue
            if not fixture.home_resolved or not fixture.away_resolved:
                continue

            snapshot = lookup_espn_match(
                espn_index,
                home_name=fixture.home_team.name,
                away_name=fixture.away_team.name,
                kickoff=fixture.date,
            )
            if snapshot is None:
                continue

            priority = 0
            if snapshot.is_live or snapshot.status in LIVE_STATUSES:
                priority = 3
            elif snapshot.status == "FT":
                priority = 2
            elif snapshot.status == "NS":
                priority = 1

            candidates.append((priority, fixture.id, snapshot))

    if not candidates:
        return None

    candidates.sort(key=lambda item: (item[0], item[2].espn_event_id), reverse=True)
    _, fixture_id, snapshot = candidates[0]
    return snapshot, fixture_id


async def _fetch_api_squad(team_name: str) -> tuple[list[RawSquadPlayer], dict[int, str]] | None:
    if not settings.api_football_configured:
        return None

    api_team_id = resolve_api_football_team_id(team_name)
    if not api_team_id:
        return None

    client = get_api_football_client()
    try:
        squad_payload = await client.get_team_squad(api_team_id)
        injuries_payload = await client.get_team_injuries(api_team_id)
    except (APIFootballError, Exception) as exc:
        logger.warning("API-Football squad unavailable for %s: %s", team_name, exc)
        return None

    if not squad_payload:
        return None

    injured: dict[int, str] = {}
    for entry in injuries_payload:
        player = entry.get("player") or {}
        pid = player.get("id")
        if pid is None:
            continue
        reason = entry.get("reason") or entry.get("type") or "Unavailable"
        injured[int(pid)] = str(reason)

    players: list[RawSquadPlayer] = []
    for player in squad_payload[0].get("players") or []:
        players.append(
            RawSquadPlayer(
                id=int(player["id"]),
                name=str(player["name"]),
                number=player.get("number"),
                position=player.get("position"),
                photo=player.get("photo"),
            )
        )

    if not players:
        return None

    return players, injured


def _build_response(
    *,
    team_id: int,
    team_name: str,
    source: str,
    players: list[RawSquadPlayer],
    injured: dict[int, str],
    starters: list[RawSquadPlayer],
    bench: list[RawSquadPlayer],
    is_live_lineup: bool = False,
    live_minute: int | None = None,
    live_fixture_id: int | None = None,
    lineup_confirmed: bool = False,
) -> TeamSquadResponse:
    by_id = {p.id: p for p in players}
    starter_ids = {p.id for p in starters}
    bench_ids = {p.id for p in bench if p.id not in starter_ids}

    injured_players: list[PlayerSummary] = []
    healthy: list[RawSquadPlayer] = []
    for player in players:
        if player.id in injured:
            injured_players.append(
                _to_summary(player, SquadCategory.INJURED, injury_reason=injured[player.id])
            )
        else:
            healthy.append(player)

    if not lineup_confirmed and not starter_ids:
        bench_ids = set()
    elif not bench_ids and lineup_confirmed:
        remaining = [p for p in healthy if p.id not in starter_ids]
        bench_ids = {p.id for p in remaining[:MATCHDAY_BENCH]}

    reserve_ids = {
        p.id for p in healthy if p.id not in starter_ids and p.id not in bench_ids
    }

    starting_xi = [_to_summary(p, SquadCategory.STARTING) for p in starters]
    substitutes = [_to_summary(p, SquadCategory.SUBSTITUTE) for p in bench]
    reserves = [_to_summary(by_id[pid], SquadCategory.RESERVE) for pid in reserve_ids if pid in by_id]

    starting_xi.sort(key=lambda p: (p.number or 99, p.name))
    substitutes.sort(key=lambda p: (p.number or 99, p.name))
    reserves.sort(key=lambda p: (p.number or 99, p.name))
    injured_players.sort(key=lambda p: (p.number or 99, p.name))

    all_players = starting_xi + substitutes + reserves + injured_players

    return TeamSquadResponse(
        team_id=team_id,
        team_name=team_name,
        source=source,
        is_live_lineup=is_live_lineup,
        live_minute=live_minute,
        live_fixture_id=live_fixture_id,
        lineup_confirmed=lineup_confirmed,
        all_players=all_players,
        starting_xi=starting_xi,
        substitutes=substitutes,
        reserves=reserves,
        injured=injured_players,
    )


async def build_team_squad(team_id: int, team_name: str) -> TeamSquadResponse:
    """Assemble squad groupings for a national team."""
    roster_source = "statsbomb"
    injured: dict[int, str] = {}
    players: list[RawSquadPlayer] = []

    api_data = await _fetch_api_squad(team_name)
    if api_data:
        players, injured = api_data
        roster_source = "api_football"

    if not players:
        players = await collect_team_squad_players(team_name)

    if not players:
        raise ValueError(f"No squad data available for {team_name}")

    await _enrich_photos(players, team_name)

    starters: list[RawSquadPlayer] = []
    bench: list[RawSquadPlayer] = []
    lineup_confirmed = False
    is_live = False
    live_minute: int | None = None
    live_fixture_id: int | None = None
    lineup_source = roster_source

    espn_ctx = await _find_espn_fixture_for_team(team_name)
    if espn_ctx is not None:
        espn_fixture, openfootball_fixture_id = espn_ctx
        espn_lineup = await fetch_espn_team_lineup(
            espn_fixture.espn_event_id,
            team_name,
        )
        if espn_lineup is not None and len(espn_lineup.starters) >= 11:
            starters = _merge_espn_players(espn_lineup.starters, players)
            bench = _merge_espn_players(espn_lineup.bench, players)
            lineup_confirmed = True
            lineup_source = "espn"
            is_live = espn_fixture.is_live or espn_fixture.status in LIVE_STATUSES
            live_minute = espn_fixture.minute
            live_fixture_id = openfootball_fixture_id

    return _build_response(
        team_id=team_id,
        team_name=team_name,
        source=lineup_source,
        players=players,
        injured=injured,
        starters=starters,
        bench=bench,
        is_live_lineup=is_live and lineup_confirmed,
        live_minute=live_minute,
        live_fixture_id=live_fixture_id,
        lineup_confirmed=lineup_confirmed,
    )
