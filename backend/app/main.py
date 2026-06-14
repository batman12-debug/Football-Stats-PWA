"""GoalMind FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import settings
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.routers import matches, news, predictions, teams
from app.scheduler import start_scheduler, stop_scheduler
from app.services.api_football import APIFootballError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _log_config_warnings() -> None:
    if settings.is_production:
        if not settings.redis_configured:
            logger.warning(
                "Production: Upstash Redis not configured — using in-memory rate limits only."
            )
        if not settings.admin_api_key.strip():
            logger.warning(
                "Production: ADMIN_API_KEY not set — match result writes are disabled."
            )
        if not settings.trusted_hosts_list:
            logger.warning(
                "Production: TRUSTED_HOSTS not set — host header validation is disabled."
            )

    if not settings.api_football_configured:
        logger.warning(
            "API_FOOTBALL_KEY not set — data sync jobs will be skipped. "
            "Copy backend/.env.example to backend/.env and add your key."
        )
    if not settings.supabase_configured:
        logger.warning(
            "SUPABASE_URL/SUPABASE_KEY not set — database sync will be skipped."
        )
    if not settings.redis_configured:
        logger.warning(
            "Upstash Redis not configured — API responses will not be cached "
            "and rate limiting uses in-memory fallback."
        )
    if not settings.allowed_cors_origins:
        logger.warning("No CORS origins configured — browser requests may be blocked.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown lifecycle."""
    _log_config_warnings()
    start_scheduler()
    yield
    stop_scheduler()


_is_prod = settings.is_production

app = FastAPI(
    title="GoalMind API",
    description="World Cup 2026 match prediction API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None if _is_prod else "/docs",
    redoc_url=None if _is_prod else "/redoc",
    openapi_url=None if _is_prod else "/openapi.json",
)

if settings.trusted_hosts_list:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts_list)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Admin-Key"],
)

app.include_router(news.router, prefix="/api/news", tags=["news"])
app.include_router(teams.router, prefix="/api/teams", tags=["teams"])
app.include_router(matches.router, prefix="/api/matches", tags=["matches"])
app.include_router(predictions.router, prefix="/api/predictions", tags=["predictions"])


@app.exception_handler(APIFootballError)
async def api_football_exception_handler(
    request: Request, exc: APIFootballError
) -> JSONResponse:
    logger.error("API-Football error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "Football data service is temporarily unavailable."},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error."},
    )


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
