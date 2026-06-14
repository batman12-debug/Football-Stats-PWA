"""APScheduler cron jobs for data sync and cache warming."""

import logging
from datetime import date, datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.db.supabase_client import (
    get_all_team_ids,
    has_live_matches,
    upsert_fixtures,
    upsert_teams,
)
from app.services.api_football import (
    WC_LEAGUE_ID,
    WC_SEASON,
    APIFootballError,
    get_api_football_client,
)

logger = logging.getLogger(__name__)

WC_TOURNAMENT_START = date(2026, 6, 11)
WC_TOURNAMENT_END = date(2026, 7, 19)

_scheduler: AsyncIOScheduler | None = None


def _is_tournament_active() -> bool:
    today = datetime.now(timezone.utc).date()
    return WC_TOURNAMENT_START <= today <= WC_TOURNAMENT_END


def _sync_prerequisites_met(job_name: str) -> bool:
    if settings.data_source != "api_football":
        logger.debug("%s skipped — DATA_SOURCE=%s (not api_football)", job_name, settings.data_source)
        return False
    if not settings.api_football_configured:
        logger.warning(
            "%s skipped — API_FOOTBALL_KEY not set (copy backend/.env.example to backend/.env)",
            job_name,
        )
        return False
    if not settings.supabase_configured:
        logger.warning(
            "%s skipped — SUPABASE_URL and SUPABASE_KEY not set",
            job_name,
        )
        return False
    return True


async def refresh_team_stats() -> None:
    """Fetch all teams and their statistics, then persist to Supabase."""
    if not _sync_prerequisites_met("refresh_team_stats"):
        return

    logger.info("Starting refresh_team_stats job")
    client = get_api_football_client()

    try:
        teams = await client.get_teams(WC_LEAGUE_ID, WC_SEASON)
        count = upsert_teams(teams)
        logger.info("Upserted %d teams", count)

        team_ids = [entry["team"]["id"] for entry in teams]
        if not team_ids:
            team_ids = get_all_team_ids(WC_LEAGUE_ID, WC_SEASON)

        stats_batch = await client.get_team_statistics_batch(
            team_ids, WC_LEAGUE_ID, WC_SEASON
        )
        logger.info("Fetched statistics for %d teams", len(stats_batch))
    except APIFootballError as exc:
        logger.error("refresh_team_stats failed: %s", exc)
    except Exception:
        logger.exception("refresh_team_stats failed")


async def refresh_fixtures() -> None:
    """Fetch and upsert fixtures. Only runs during tournament dates."""
    if not _is_tournament_active():
        logger.debug("Skipping refresh_fixtures — outside tournament window")
        return
    if not _sync_prerequisites_met("refresh_fixtures"):
        return

    logger.info("Starting refresh_fixtures job")
    client = get_api_football_client()

    try:
        fixtures = await client.get_fixtures(WC_LEAGUE_ID, WC_SEASON)
        count = upsert_fixtures(fixtures)
        logger.info("Upserted %d fixtures", count)
    except APIFootballError as exc:
        logger.error("refresh_fixtures failed: %s", exc)
    except Exception:
        logger.exception("refresh_fixtures failed")


async def refresh_live_matches() -> None:
    """Poll live fixtures every 60s, but only when matches are in progress."""
    if not settings.supabase_configured or not settings.api_football_configured:
        return
    try:
        if not has_live_matches(WC_LEAGUE_ID, WC_SEASON):
            return
    except Exception:
        logger.exception("refresh_live_matches skipped — could not query Supabase")
        return

    logger.info("Starting refresh_live_matches job")
    client = get_api_football_client()

    try:
        live_fixtures = await client.get_live_fixtures(WC_LEAGUE_ID, WC_SEASON)
        if live_fixtures:
            count = upsert_fixtures(live_fixtures)
            logger.info("Updated %d live fixtures", count)
    except APIFootballError as exc:
        logger.error("refresh_live_matches failed: %s", exc)
    except Exception:
        logger.exception("refresh_live_matches failed")


def start_scheduler() -> None:
    """Start background scheduled jobs."""
    global _scheduler

    if _scheduler is not None:
        return

    _scheduler = AsyncIOScheduler()

    _scheduler.add_job(
        refresh_team_stats,
        trigger="interval",
        hours=24,
        id="refresh_team_stats",
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc),
    )

    _scheduler.add_job(
        refresh_fixtures,
        trigger="interval",
        hours=6,
        id="refresh_fixtures",
        replace_existing=True,
    )

    _scheduler.add_job(
        refresh_live_matches,
        trigger="interval",
        seconds=60,
        id="refresh_live_matches",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("Scheduler started with 3 jobs")


def stop_scheduler() -> None:
    """Gracefully shut down the scheduler."""
    global _scheduler

    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped")
