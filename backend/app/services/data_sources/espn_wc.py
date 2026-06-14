"""ESPN fifa.world scoreboard — live scores without API keys."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.services.cache import get_json_cached, set_json_cached
from app.services.data_sources.team_names import normalize_team_name

logger = logging.getLogger(__name__)

ESPN_SCOREBOARD_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
)
ESPN_SUMMARY_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/summary"
)
USER_AGENT = "GoalMind/1.0 (+https://github.com/goalmind; espn wc scoreboard)"
CACHE_TTL_LIVE = 30
CACHE_TTL_RECENT = 300
CACHE_TTL_LINEUP = 120

_memory_cache: dict[str, tuple[float, dict[tuple[str, str, str], EspnMatchSnapshot]]] = {}


@dataclass(frozen=True)
class EspnLineupPlayer:
    name: str
    number: int | None
    position: str | None
    is_starter: bool


@dataclass(frozen=True)
class EspnTeamLineup:
    team_name: str
    formation: str | None
    starters: tuple[EspnLineupPlayer, ...]
    bench: tuple[EspnLineupPlayer, ...]


@dataclass(frozen=True)
class EspnMatchSnapshot:
    espn_event_id: str
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    status: str
    minute: int | None
    clock_display: str | None
    is_live: bool


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_score(value: Any) -> int:
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _map_espn_status(type_name: str, state: str) -> tuple[str, bool]:
    name = (type_name or "").upper()
    if name in {"STATUS_FULL_TIME", "STATUS_FINAL"} or state == "post":
        return "FT", False
    if name == "STATUS_HALFTIME":
        return "HT", True
    if name in {"STATUS_FIRST_HALF"}:
        return "1H", True
    if name in {"STATUS_SECOND_HALF"}:
        return "2H", True
    if name in {"STATUS_IN_PROGRESS", "STATUS_END_PERIOD"}:
        return "LIVE", True
    if name == "STATUS_SCHEDULED" or state == "pre":
        return "NS", False
    if state == "in":
        return "LIVE", True
    return "NS", False


def _parse_clock_minute(clock: str | None) -> int | None:
    if not clock:
        return None
    clock = clock.strip()
    if "+" in clock:
        left, _, right = clock.partition("+")
        base_str = "".join(ch for ch in left if ch.isdigit())
        extra_str = "".join(ch for ch in right if ch.isdigit())
        if base_str and extra_str:
            return int(base_str) + int(extra_str)
        if base_str:
            return int(base_str)
    digits = "".join(ch for ch in clock if ch.isdigit())
    if not digits:
        return None
    return int(digits)


def _fixture_key(home: str, away: str, kickoff: datetime) -> tuple[str, str, str]:
    day = kickoff.astimezone(timezone.utc).strftime("%Y-%m-%d")
    return normalize_team_name(home), normalize_team_name(away), day


def _parse_event(event: dict[str, Any]) -> EspnMatchSnapshot | None:
    competition = (event.get("competitions") or [{}])[0]
    competitors = competition.get("competitors") or []
    if len(competitors) < 2:
        return None

    home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
    away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])

    home_name = (home.get("team") or {}).get("displayName") or ""
    away_name = (away.get("team") or {}).get("displayName") or ""
    if not home_name or not away_name:
        return None

    status_block = event.get("status") or competition.get("status") or {}
    type_info = status_block.get("type") or {}
    status, is_live = _map_espn_status(type_info.get("name", ""), type_info.get("state", ""))
    clock = status_block.get("displayClock")

    return EspnMatchSnapshot(
        espn_event_id=str(event.get("id", "")),
        home_team=home_name,
        away_team=away_name,
        home_goals=_parse_score(home.get("score")),
        away_goals=_parse_score(away.get("score")),
        status=status,
        minute=_parse_clock_minute(clock),
        clock_display=clock,
        is_live=is_live,
    )


def _index_events(events: list[dict[str, Any]]) -> dict[tuple[str, str, str], EspnMatchSnapshot]:
    index: dict[tuple[str, str, str], EspnMatchSnapshot] = {}
    for event in events:
        snapshot = _parse_event(event)
        if snapshot is None:
            continue

        competition = (event.get("competitions") or [{}])[0]
        date_str = competition.get("date") or event.get("date")
        if not date_str:
            continue
        try:
            kickoff = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            continue

        key = _fixture_key(snapshot.home_team, snapshot.away_team, kickoff)
        index[key] = snapshot
    return index


async def _fetch_scoreboard(*, dates: str | None = None) -> list[dict[str, Any]]:
    params: dict[str, str] = {}
    if dates:
        params["dates"] = dates

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(12.0, connect=5.0),
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    ) as client:
        response = await client.get(ESPN_SCOREBOARD_URL, params=params)
        response.raise_for_status()
        payload = response.json()

    return payload.get("events") or []


async def build_espn_wc_index(*, days_back: int = 3) -> dict[tuple[str, str, str], EspnMatchSnapshot]:
    """Fetch ESPN scoreboards for recent days and index by teams + UTC date."""
    cache_key = f"espn:wc:index:{days_back}"
    mem = _memory_cache.get(cache_key)
    if mem and time.monotonic() < mem[0]:
        return mem[1]

    cached = await get_json_cached(cache_key)
    if cached is not None:
        index = {
            tuple(json.loads(k)): EspnMatchSnapshot(**v)
            for k, v in cached.items()
        }
        _memory_cache[cache_key] = (time.monotonic() + CACHE_TTL_LIVE, index)
        return index

    index: dict[tuple[str, str, str], EspnMatchSnapshot] = {}
    today = _utcnow().date()

    date_params: list[str | None] = [None]
    for offset in range(days_back + 1):
        day = today - timedelta(days=offset)
        date_params.append(day.strftime("%Y%m%d"))

    seen_dates: set[str | None] = set()
    for dates in date_params:
        if dates in seen_dates:
            continue
        seen_dates.add(dates)
        try:
            events = await _fetch_scoreboard(dates=dates)
            index.update(_index_events(events))
        except Exception as exc:
            logger.warning("ESPN scoreboard fetch failed (dates=%s): %s", dates, exc)

    ttl = CACHE_TTL_LIVE if any(s.is_live for s in index.values()) else CACHE_TTL_RECENT
    serialized = {
        json.dumps(list(key)): {
            "espn_event_id": s.espn_event_id,
            "home_team": s.home_team,
            "away_team": s.away_team,
            "home_goals": s.home_goals,
            "away_goals": s.away_goals,
            "status": s.status,
            "minute": s.minute,
            "clock_display": s.clock_display,
            "is_live": s.is_live,
        }
        for key, s in index.items()
    }
    _memory_cache[cache_key] = (time.monotonic() + ttl, index)
    await set_json_cached(cache_key, serialized, ttl_seconds=ttl)
    return index


def lookup_espn_match(
    index: dict[tuple[str, str, str], EspnMatchSnapshot],
    *,
    home_name: str,
    away_name: str,
    kickoff: datetime,
) -> EspnMatchSnapshot | None:
    """Find an ESPN snapshot for a fixture, matching either home/away orientation."""
    if kickoff.tzinfo is None:
        kickoff = kickoff.replace(tzinfo=timezone.utc)

    home_key = normalize_team_name(home_name)
    away_key = normalize_team_name(away_name)

    # OpenFootball kickoffs are UTC; ESPN indexes by local calendar day — try ±1 day.
    for day_offset in (0, -1, 1):
        day = (kickoff + timedelta(days=day_offset)).astimezone(timezone.utc).strftime("%Y-%m-%d")
        hit = index.get((home_key, away_key, day))
        if hit is not None:
            return hit

        reverse = index.get((away_key, home_key, day))
        if reverse is not None:
            return EspnMatchSnapshot(
                espn_event_id=reverse.espn_event_id,
                home_team=home_name,
                away_team=away_name,
                home_goals=reverse.away_goals,
                away_goals=reverse.home_goals,
                status=reverse.status,
                minute=reverse.minute,
                clock_display=reverse.clock_display,
                is_live=reverse.is_live,
            )

    return None


def _person_key(name: str) -> str:
    return normalize_team_name(name)


async def fetch_espn_match_lineups(espn_event_id: str) -> dict[str, EspnTeamLineup]:
    """Return confirmed lineups keyed by normalized team name."""
    cache_key = f"espn:wc:lineup:{espn_event_id}"
    cached = await get_json_cached(cache_key)
    if cached is not None:
        return {
            key: EspnTeamLineup(
                team_name=data["team_name"],
                formation=data.get("formation"),
                starters=tuple(EspnLineupPlayer(**p) for p in data["starters"]),
                bench=tuple(EspnLineupPlayer(**p) for p in data["bench"]),
            )
            for key, data in cached.items()
        }

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(12.0, connect=5.0),
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    ) as client:
        response = await client.get(ESPN_SUMMARY_URL, params={"event": espn_event_id})
        response.raise_for_status()
        payload = response.json()

    lineups: dict[str, EspnTeamLineup] = {}
    serialized: dict[str, dict[str, Any]] = {}

    for block in payload.get("rosters") or []:
        team_name = (block.get("team") or {}).get("displayName") or ""
        if not team_name:
            continue

        starters: list[EspnLineupPlayer] = []
        bench: list[EspnLineupPlayer] = []
        for entry in block.get("roster") or []:
            athlete = entry.get("athlete") or {}
            name = (athlete.get("displayName") or athlete.get("shortName") or "").strip()
            if not name:
                continue
            player = EspnLineupPlayer(
                name=name,
                number=_parse_optional_int(entry.get("jersey")),
                position=(entry.get("position") or {}).get("name")
                if isinstance(entry.get("position"), dict)
                else entry.get("position"),
                is_starter=bool(entry.get("starter")),
            )
            if player.is_starter:
                starters.append(player)
            else:
                bench.append(player)

        if len(starters) < 11:
            continue

        team_key = normalize_team_name(team_name)
        lineup = EspnTeamLineup(
            team_name=team_name,
            formation=block.get("formation"),
            starters=tuple(starters[:11]),
            bench=tuple(bench),
        )
        lineups[team_key] = lineup
        serialized[team_key] = {
            "team_name": team_name,
            "formation": lineup.formation,
            "starters": [p.__dict__ for p in lineup.starters],
            "bench": [p.__dict__ for p in lineup.bench],
        }

    await set_json_cached(cache_key, serialized, ttl_seconds=CACHE_TTL_LINEUP)
    return lineups


def _parse_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class EspnTeamBoxStats:
    """Team statistics from ESPN match summary boxscore."""

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


def _espn_stat_int(statistics: list[dict[str, Any]], name: str) -> int:
    for row in statistics:
        if row.get("name") == name:
            return _parse_score(row.get("displayValue"))
    return 0


def _espn_stat_float(statistics: list[dict[str, Any]], name: str) -> float:
    for row in statistics:
        if row.get("name") == name:
            raw = row.get("displayValue")
            if raw is None:
                return 0.0
            try:
                return float(str(raw).replace("%", "").strip())
            except ValueError:
                return 0.0
    return 0.0


def parse_espn_team_box_stats(statistics: list[dict[str, Any]]) -> EspnTeamBoxStats:
    """Map ESPN boxscore statistics array to normalized live team stats."""
    passes = _espn_stat_int(statistics, "totalPasses")
    accurate = _espn_stat_int(statistics, "accuratePasses")
    pass_pct = _espn_stat_float(statistics, "passPct")
    if 0 < pass_pct <= 1:
        pass_pct *= 100
    elif pass_pct == 0 and passes > 0 and accurate > 0:
        pass_pct = round((accurate / passes) * 100, 1)

    return EspnTeamBoxStats(
        shots=_espn_stat_int(statistics, "totalShots"),
        shots_on_target=_espn_stat_int(statistics, "shotsOnTarget"),
        possession=_espn_stat_float(statistics, "possessionPct"),
        passes=passes,
        pass_accuracy=pass_pct,
        fouls=_espn_stat_int(statistics, "foulsCommitted"),
        yellow_cards=_espn_stat_int(statistics, "yellowCards"),
        red_cards=_espn_stat_int(statistics, "redCards"),
        offsides=_espn_stat_int(statistics, "offsides"),
        corners=_espn_stat_int(statistics, "wonCorners"),
    )


async def fetch_espn_match_boxscore(
    espn_event_id: str,
) -> list[tuple[str, EspnTeamBoxStats]] | None:
    """Fetch per-team live boxscore stats from ESPN summary (30s cache when live)."""
    cache_key = f"espn:wc:boxscore:{espn_event_id}"
    cached = await get_json_cached(cache_key)
    if cached is not None:
        return [
            (entry["team_name"], EspnTeamBoxStats(**entry["stats"]))
            for entry in cached
        ]

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(12.0, connect=5.0),
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    ) as client:
        response = await client.get(ESPN_SUMMARY_URL, params={"event": espn_event_id})
        response.raise_for_status()
        payload = response.json()

    teams = (payload.get("boxscore") or {}).get("teams") or []
    if len(teams) < 2:
        return None

    parsed: list[tuple[str, EspnTeamBoxStats]] = []
    serialized: list[dict[str, Any]] = []
    for block in teams:
        team_name = (block.get("team") or {}).get("displayName") or ""
        if not team_name:
            continue
        stats = parse_espn_team_box_stats(block.get("statistics") or [])
        parsed.append((team_name, stats))
        serialized.append({"team_name": team_name, "stats": stats.__dict__})

    if len(parsed) < 2:
        return None

    await set_json_cached(cache_key, serialized, ttl_seconds=CACHE_TTL_LIVE)
    return parsed


async def fetch_espn_team_lineup(
    espn_event_id: str,
    team_name: str,
) -> EspnTeamLineup | None:
    lineups = await fetch_espn_match_lineups(espn_event_id)
    return lineups.get(normalize_team_name(team_name))
