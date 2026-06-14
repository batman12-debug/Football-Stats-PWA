"""Supabase PostgreSQL client and data access helpers."""

from datetime import datetime, timezone
from typing import Any

from supabase import Client, create_client

from app.config import settings

WC_LEAGUE_ID = settings.wc_league_id
WC_SEASON = settings.wc_season

_supabase_client: Client | None = None

LIVE_STATUSES = frozenset({"1H", "2H", "HT", "ET", "BT", "P", "LIVE", "INT"})


def get_supabase_client() -> Client:
    """Return a configured Supabase client instance."""
    global _supabase_client
    if _supabase_client is None:
        if not settings.supabase_url or not settings.supabase_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set")
        _supabase_client = create_client(settings.supabase_url, settings.supabase_key)
    return _supabase_client


def _parse_team_record(entry: dict, league_id: int, season: int) -> dict[str, Any]:
    team = entry.get("team", entry)
    return {
        "id": team["id"],
        "name": team["name"],
        "code": team.get("code"),
        "logo": team.get("logo"),
        "country": team.get("country"),
        "league_id": league_id,
        "season": season,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _parse_fixture_record(entry: dict, league_id: int, season: int) -> dict[str, Any]:
    fixture = entry["fixture"]
    teams = entry["teams"]
    goals = entry.get("goals", {})
    status = fixture.get("status", {})

    return {
        "id": fixture["id"],
        "league_id": league_id,
        "season": season,
        "date": fixture["date"],
        "status": status.get("short", "NS"),
        "status_long": status.get("long"),
        "home_team_id": teams["home"]["id"],
        "away_team_id": teams["away"]["id"],
        "home_team_name": teams["home"]["name"],
        "away_team_name": teams["away"]["name"],
        "home_goals": goals.get("home"),
        "away_goals": goals.get("away"),
        "venue_name": fixture.get("venue", {}).get("name"),
        "venue_city": fixture.get("venue", {}).get("city"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def upsert_teams(
    teams: list[dict],
    league_id: int = WC_LEAGUE_ID,
    season: int = WC_SEASON,
) -> int:
    """Upsert team records from API-Football response. Returns count upserted."""
    if not teams:
        return 0

    records = [_parse_team_record(entry, league_id, season) for entry in teams]
    client = get_supabase_client()
    client.table("teams").upsert(records, on_conflict="id").execute()
    return len(records)


def upsert_fixtures(
    fixtures: list[dict],
    league_id: int = WC_LEAGUE_ID,
    season: int = WC_SEASON,
) -> int:
    """Upsert fixture records from API-Football response. Returns count upserted."""
    if not fixtures:
        return 0

    records = [_parse_fixture_record(entry, league_id, season) for entry in fixtures]
    client = get_supabase_client()
    client.table("fixtures").upsert(records, on_conflict="id").execute()
    return len(records)


def get_h2h_history(team1_id: int, team2_id: int, limit: int = 10) -> list[dict]:
    """Return the last N head-to-head matches between two teams from the database."""
    client = get_supabase_client()

    response = (
        client.table("fixtures")
        .select("*")
        .or_(
            f"and(home_team_id.eq.{team1_id},away_team_id.eq.{team2_id}),"
            f"and(home_team_id.eq.{team2_id},away_team_id.eq.{team1_id})"
        )
        .eq("status", "FT")
        .order("date", desc=True)
        .limit(limit)
        .execute()
    )

    return response.data or []


def has_live_matches(league_id: int, season: int) -> bool:
    """Check if any fixtures are currently live in the database."""
    client = get_supabase_client()
    response = (
        client.table("fixtures")
        .select("id")
        .eq("league_id", league_id)
        .eq("season", season)
        .in_("status", list(LIVE_STATUSES))
        .limit(1)
        .execute()
    )
    return bool(response.data)


def get_all_team_ids(league_id: int, season: int) -> list[int]:
    """Return all team IDs stored for a league and season."""
    client = get_supabase_client()
    response = (
        client.table("teams")
        .select("id")
        .eq("league_id", league_id)
        .eq("season", season)
        .execute()
    )
    return [row["id"] for row in (response.data or [])]
