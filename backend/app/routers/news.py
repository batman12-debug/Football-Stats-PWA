"""News and transfer market routes."""

import logging

from fastapi import APIRouter, HTTPException, Query

from app.models.news import NewsFeedResponse
from app.security.errors import SERVICE_UNAVAILABLE
from app.services.data_sources.news_feeds import (
    NEWS_CATEGORIES,
    fetch_transfer_items,
    get_news_feed,
)

logger = logging.getLogger(__name__)
router = APIRouter()

_ALLOWED_CATEGORIES = {category.lower() for category in NEWS_CATEGORIES}


@router.get("", response_model=NewsFeedResponse)
async def get_news(
    category: str | None = Query(
        default=None,
        max_length=64,
        description="Filter by league/category",
    ),
    limit: int = Query(default=40, ge=1, le=80),
) -> NewsFeedResponse:
    """Latest football news and transfer updates."""
    if category is not None and category.lower() not in _ALLOWED_CATEGORIES:
        raise HTTPException(status_code=400, detail="Invalid category.")

    try:
        if category and category.lower() == "transfers":
            transfers = await fetch_transfer_items(limit=limit)
            return NewsFeedResponse(
                articles=[],
                transfers=transfers,
                categories=NEWS_CATEGORIES,
            )
        return await get_news_feed(category=category, limit=limit)
    except Exception as exc:
        logger.error("Failed to fetch news feed: %s", exc)
        raise HTTPException(status_code=503, detail=SERVICE_UNAVAILABLE) from exc


@router.get("/transfers")
async def get_transfers(limit: int = Query(default=30, ge=1, le=60)):
    """Latest transfer market activity."""
    try:
        return await fetch_transfer_items(limit=limit)
    except Exception as exc:
        logger.error("Failed to fetch transfers: %s", exc)
        raise HTTPException(status_code=503, detail=SERVICE_UNAVAILABLE) from exc
