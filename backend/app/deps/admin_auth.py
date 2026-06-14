"""Admin authentication for privileged write endpoints."""

import secrets

from fastapi import Header, HTTPException

from app.config import settings


async def require_admin_api_key(
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> None:
    """Verify the caller holds the configured admin API key."""
    configured = settings.admin_api_key.strip()
    if not configured:
        raise HTTPException(
            status_code=503,
            detail="Admin operations are disabled.",
        )

    if not x_admin_key or not secrets.compare_digest(x_admin_key, configured):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized.",
        )
