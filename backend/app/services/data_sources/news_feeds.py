"""Aggregate football news and transfer data from public RSS feeds."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from xml.etree import ElementTree

import httpx

from app.config import settings
from app.models.news import NewsArticle, NewsFeedResponse, TransferItem
from app.services.api_football import APIFootballError, get_api_football_client
from app.services.cache import get_json_cached, set_json_cached

logger = logging.getLogger(__name__)

CACHE_TTL_NEWS = 900  # 15 minutes
CACHE_TTL_TRANSFERS = 1800  # 30 minutes

NEWS_CATEGORIES: list[str] = sorted(
    {
        "All",
        "World Cup",
        "Premier League",
        "La Liga",
        "Serie A",
        "Bundesliga",
        "Ligue 1",
        "Transfers",
    }
)

# In-process fallback cache so feeds are not re-downloaded on every request
# when Redis is unavailable.
_memory_cache: dict[str, tuple[float, Any]] = {}


def _memory_get(key: str) -> Any | None:
    entry = _memory_cache.get(key)
    if entry is None:
        return None
    expires_at, value = entry
    if time.monotonic() > expires_at:
        _memory_cache.pop(key, None)
        return None
    return value


def _memory_set(key: str, value: Any, ttl_seconds: int) -> None:
    _memory_cache[key] = (time.monotonic() + ttl_seconds, value)

USER_AGENT = "GoalMind/1.0 (+https://github.com/goalmind; news aggregator)"
MAX_RSS_BYTES = 2_000_000  # 2 MB per feed

NEWS_FEEDS: list[dict[str, str]] = [
    {
        "url": "https://feeds.bbci.co.uk/sport/football/world-cup/rss.xml",
        "source": "BBC Sport",
        "category": "World Cup",
    },
    {
        "url": "https://feeds.bbci.co.uk/sport/football/premier-league/rss.xml",
        "source": "BBC Sport",
        "category": "Premier League",
    },
    {
        "url": "https://feeds.bbci.co.uk/sport/football/rss.xml",
        "source": "BBC Sport",
        "category": "Football",
    },
    {
        "url": "https://www.espn.com/espn/rss/soccer/news",
        "source": "ESPN",
        "category": "Football",
    },
    {
        "url": "https://www.theguardian.com/football/rss",
        "source": "The Guardian",
        "category": "Football",
    },
    {
        "url": "https://www.theguardian.com/football/bundesligafootball/rss",
        "source": "The Guardian",
        "category": "Bundesliga",
    },
    {
        "url": "https://football-italia.net/feed/",
        "source": "Football Italia",
        "category": "Serie A",
    },
]

TRANSFER_FEEDS: list[dict[str, str]] = [
    {
        "url": "https://www.theguardian.com/football/transfer-window/rss",
        "source": "The Guardian",
    },
]

# Top-league team IDs for API-Football transfer lookups (when quota allows).
TOP_TEAM_IDS: dict[str, list[int]] = {
    "Premier League": [40, 42, 50, 49, 33, 47],  # Liverpool, Arsenal, Man City, Chelsea, Man Utd, Spurs
    "La Liga": [541, 529, 530, 531],  # Real Madrid, Barcelona, Atletico, Athletic
    "Serie A": [489, 505, 496, 492],  # Milan, Inter, Juventus, Napoli
    "Bundesliga": [157, 165, 173, 168],  # Bayern, Dortmund, Leverkusen, Leipzig
    "Ligue 1": [85, 81, 91, 80],  # PSG, Marseille, Monaco, Lyon
}

CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "World Cup": ("world cup", "fifa", "2026"),
    "Premier League": ("premier league", "epl", "manchester", "liverpool", "arsenal", "chelsea", "tottenham"),
    "La Liga": ("la liga", "real madrid", "barcelona", "atletico", "sevilla"),
    "Serie A": ("serie a", "juventus", "inter milan", "ac milan", "napoli", "roma"),
    "Bundesliga": ("bundesliga", "bayern", "dortmund", "leverkusen"),
    "Ligue 1": ("ligue 1", "psg", "paris saint", "marseille", "monaco", "lyon"),
    "Transfers": ("transfer", "signs", "signed", "deal", "move to", "joins", "loan", "fee"),
}


def _stable_id(prefix: str, value: str) -> str:
    digest = hashlib.md5(value.encode(), usedforsecurity=False).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _strip_html(text: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", text or "")
    cleaned = unescape(cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _parse_pub_date(raw: str | None) -> str:
    if not raw:
        return datetime.now(timezone.utc).isoformat()
    try:
        return parsedate_to_datetime(raw).astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError, IndexError):
        return datetime.now(timezone.utc).isoformat()


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


MEDIA_NS = {"media": "http://search.yahoo.com/mrss/"}

OG_IMAGE_RE = re.compile(
    r'<meta[^>]+(?:property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']'
    r'|content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\'])',
    re.I,
)

BBC_STANDARD_WIDTH = 976
BBC_LEGACY_SIZE = "976x549"
GUARDIAN_DISPLAY_WIDTH = 1200
OG_FETCH_LIMIT = 24
OG_FETCH_CONCURRENCY = 6
MAX_OG_HTML_BYTES = 350_000


def _image_resolution_score(url: str) -> int:
    width_match = re.search(r"[?&]width=(\d+)", url, re.I)
    if width_match:
        return int(width_match.group(1))

    standard_match = re.search(r"/standard/(\d+)/", url)
    if standard_match:
        return int(standard_match.group(1))

    ic_match = re.search(r"/images/ic/(\d+)x(\d+)/", url)
    if ic_match:
        return int(ic_match.group(1))

    dim_match = re.search(r"-(\d+)x(\d+)\.(?:jpe?g|png|webp|gif)(?:\?|$)", url, re.I)
    if dim_match:
        return int(dim_match.group(1))

    combiner_match = re.search(r"[?&]w=(\d+)", url, re.I)
    if combiner_match:
        return int(combiner_match.group(1))

    return 0


def _pick_best_image(urls: list[str]) -> str | None:
    cleaned = [url.strip() for url in urls if url and url.strip()]
    if not cleaned:
        return None
    return max(cleaned, key=_image_resolution_score)


def _upgrade_image_url(url: str) -> str:
    upgraded = url.strip()

    upgraded = re.sub(
        r"/ace/standard/\d+/",
        f"/ace/standard/{BBC_STANDARD_WIDTH}/",
        upgraded,
    )
    upgraded = re.sub(
        r"/images/ic/\d+x\d+/",
        f"/images/ic/{BBC_LEGACY_SIZE}/",
        upgraded,
    )

    if "i.guim.co.uk" in upgraded:
        parsed = urlparse(upgraded)
        query = parse_qs(parsed.query, keep_blank_values=True)
        query["width"] = [str(GUARDIAN_DISPLAY_WIDTH)]
        query["quality"] = ["85"]
        query["auto"] = ["format"]
        query["fit"] = ["max"]
        upgraded = urlunparse(parsed._replace(query=urlencode(query, doseq=True)))

    upgraded = re.sub(
        r"-(\d+)x(\d+)(\.(?:jpe?g|png|webp|gif))(?=\?|$)",
        r"\3",
        upgraded,
        flags=re.I,
    )

    if "espncdn.com/combiner/i" in upgraded and "w=" not in upgraded.lower():
        separator = "&" if "?" in upgraded else "?"
        upgraded = f"{upgraded}{separator}w=1280"

    return upgraded


def _find_image(item: ElementTree.Element) -> str | None:
    candidates: list[str] = []

    for child in item:
        name = _local_name(child.tag)
        if name == "enclosure" and (child.attrib.get("type") or "").startswith("image"):
            url = child.attrib.get("url")
            if url:
                candidates.append(url)
        if name in {"content", "thumbnail"} and child.attrib.get("url"):
            candidates.append(child.attrib["url"])

    thumb = item.find("media:thumbnail", MEDIA_NS)
    if thumb is not None and thumb.attrib.get("url"):
        candidates.append(thumb.attrib["url"])

    for content in item.findall("media:content", MEDIA_NS):
        medium = (content.attrib.get("medium") or "").lower()
        mime = (content.attrib.get("type") or "").lower()
        url = content.attrib.get("url")
        if url and (medium == "image" or mime.startswith("image")):
            candidates.append(url)

    description = unescape(item.findtext("description") or "")
    for match in re.finditer(r"""src=["'](https://[^"']+)["']""", description, re.I):
        candidates.append(match.group(1))

    best = _pick_best_image(candidates)
    return _upgrade_image_url(best) if best else None


async def _fetch_og_image(client: httpx.AsyncClient, url: str) -> str | None:
    try:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            chunks: list[bytes] = []
            total = 0
            async for chunk in response.aiter_bytes():
                chunks.append(chunk)
                total += len(chunk)
                if total >= MAX_OG_HTML_BYTES:
                    break
        html = b"".join(chunks).decode("utf-8", errors="replace")
        match = OG_IMAGE_RE.search(html)
        if not match:
            return None
        image_url = unescape(match.group(1) or match.group(2) or "").strip()
        return _upgrade_image_url(image_url) if image_url else None
    except Exception as exc:
        logger.debug("og:image fetch failed for %s: %s", url, exc)
        return None


async def _enrich_missing_images(items: list[dict[str, Any]]) -> None:
    missing = [item for item in items if not item.get("image_url")][:OG_FETCH_LIMIT]
    if not missing:
        return

    sem = asyncio.Semaphore(OG_FETCH_CONCURRENCY)

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(12.0, connect=4.0),
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    ) as client:

        async def enrich(item: dict[str, Any]) -> None:
            async with sem:
                item["image_url"] = await _fetch_og_image(client, item["link"])

        await asyncio.gather(*(enrich(item) for item in missing))


def _parse_rss(xml_text: str) -> list[dict[str, Any]]:
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as exc:
        logger.warning("RSS parse error: %s", exc)
        return []

    items: list[dict[str, Any]] = []
    for item in root.iter():
        if _local_name(item.tag) != "item":
            continue

        title = _strip_html(item.findtext("title") or "")
        link = (item.findtext("link") or "").strip()
        if not title or not link:
            continue

        items.append(
            {
                "title": title,
                "link": link,
                "summary": _strip_html(item.findtext("description") or "")[:400],
                "published_at": _parse_pub_date(item.findtext("pubDate")),
                "image_url": _find_image(item),
            }
        )
    return items


def _infer_categories(title: str, summary: str, default: str) -> list[str]:
    blob = f"{title} {summary}".lower()
    categories = {default} if default != "Football" else set()

    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in blob for keyword in keywords):
            categories.add(category)

    if not categories:
        categories.add("Football")

    return sorted(categories)


def _parse_transfer_from_text(title: str, summary: str) -> tuple[str, str | None, str | None, str | None]:
    """Best-effort extraction of player and clubs from headline text."""
    text = f"{title}. {summary}"

    # "X joins Y from Z" / "X signs for Y"
    patterns = [
        r"^(?P<player>.+?)\s+(?:joins|signs for|signs with|moves to|completes move to)\s+(?P<to>.+?)(?:\s+from\s+(?P<from>.+?))?(?:\.|$)",
        r"^(?P<to>.+?)\s+(?:sign|signs|complete signing of|agree deal for)\s+(?P<player>.+?)(?:\s+from\s+(?P<from>.+?))?(?:\.|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            groups = match.groupdict()
            player = (groups.get("player") or "").strip(" .'\"")
            to_club = (groups.get("to") or "").strip(" .'\"")
            from_club = (groups.get("from") or "").strip(" .'\"") or None
            fee_match = re.search(r"(€|£|\$)\s?[\d,.]+[mkMK]?|\bfree\b|\bloan\b", text, re.I)
            fee = fee_match.group(0) if fee_match else None
            return player or title, from_club, to_club or None, fee

    fee_match = re.search(r"(€|£|\$)\s?[\d,.]+[mkMK]?|\bfree transfer\b|\bon loan\b", text, re.I)
    fee = fee_match.group(0) if fee_match else None
    return title, None, None, fee


async def _fetch_feed(url: str) -> list[dict[str, Any]]:
    cache_key = f"rss:{hashlib.md5(url.encode(), usedforsecurity=False).hexdigest()}"
    cached = _memory_get(cache_key)
    if cached is None:
        cached = await get_json_cached(cache_key)
    if cached is not None:
        for item in cached:
            image_url = item.get("image_url")
            if image_url:
                item["image_url"] = _upgrade_image_url(image_url)
        _memory_set(cache_key, cached, ttl_seconds=CACHE_TTL_NEWS)
        return cached

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(15.0, connect=5.0),
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        content_length = response.headers.get("Content-Length")
        if content_length is not None:
            try:
                if int(content_length) > MAX_RSS_BYTES:
                    logger.warning("RSS feed too large (Content-Length): %s", url)
                    return []
            except ValueError:
                pass
        body = response.content
        if len(body) > MAX_RSS_BYTES:
            logger.warning("RSS feed too large (%s bytes): %s", len(body), url)
            return []
        items = _parse_rss(body.decode("utf-8", errors="replace"))

    _memory_set(cache_key, items, ttl_seconds=CACHE_TTL_NEWS)
    await set_json_cached(cache_key, items, ttl_seconds=CACHE_TTL_NEWS)
    return items


async def _fetch_feeds(
    feeds: list[dict[str, str]],
) -> list[tuple[dict[str, str], list[dict[str, Any]]]]:
    """Fetch several feeds concurrently; failed feeds yield empty item lists."""

    async def safe_fetch(feed: dict[str, str]) -> tuple[dict[str, str], list[dict[str, Any]]]:
        try:
            return feed, await _fetch_feed(feed["url"])
        except Exception as exc:
            logger.warning("Failed to fetch feed %s: %s", feed["url"], exc)
            return feed, []

    return list(await asyncio.gather(*(safe_fetch(feed) for feed in feeds)))


async def fetch_news_articles(*, category: str | None = None, limit: int = 40) -> list[NewsArticle]:
    articles: list[NewsArticle] = []
    seen: set[str] = set()
    raw_items: list[dict[str, Any]] = []

    for feed, items in await _fetch_feeds(NEWS_FEEDS):
        for item in items:
            link = item["link"]
            if link in seen:
                continue
            seen.add(link)

            categories = _infer_categories(item["title"], item["summary"], feed["category"])
            primary = feed["category"] if feed["category"] != "Football" else categories[0]

            if category and category.lower() not in {c.lower() for c in categories}:
                continue

            raw_items.append({**item, "source": feed["source"], "category": primary})

    raw_items.sort(key=lambda item: item["published_at"], reverse=True)
    await _enrich_missing_images(raw_items[: max(limit, OG_FETCH_LIMIT)])

    for item in raw_items[:limit]:
        image_url = item.get("image_url")
        if image_url:
            image_url = _upgrade_image_url(image_url)

        articles.append(
            NewsArticle(
                id=_stable_id("news", item["link"]),
                title=item["title"],
                summary=item["summary"],
                url=item["link"],
                source=item["source"],
                category=item["category"],
                published_at=item["published_at"],
                image_url=image_url,
            )
        )

    return articles


async def _fetch_api_transfers(limit: int) -> list[TransferItem]:
    if not settings.api_football_configured:
        return []

    client = get_api_football_client()
    transfers: list[TransferItem] = []
    seen_ids: set[str] = set()
    cutoff = "2024-01-01"

    for team_ids in TOP_TEAM_IDS.values():
        for team_id in team_ids:
            try:
                payload = await client.get_team_transfers(team_id)
            except APIFootballError as exc:
                # Quota/rate-limit failures affect every subsequent call too,
                # so stop instead of hammering the remaining teams.
                logger.info("API-Football transfers unavailable (%s); using RSS fallback", exc)
                transfers.sort(key=lambda t: t.date, reverse=True)
                return transfers[:limit]
            except Exception as exc:
                logger.debug("Transfer fetch failed for team %s: %s", team_id, exc)
                continue

            for record in payload or []:
                player = record.get("player") or {}
                player_name = player.get("name") or "Unknown"
                for entry in record.get("transfers") or []:
                    date = entry.get("date") or ""
                    if date < cutoff:
                        continue
                    teams = entry.get("teams") or {}
                    team_in = teams.get("in") or {}
                    team_out = teams.get("out") or {}
                    item_id = _stable_id(
                        "transfer", f"{player.get('id')}:{date}:{team_in.get('id')}"
                    )
                    if item_id in seen_ids:
                        continue
                    seen_ids.add(item_id)
                    transfers.append(
                        TransferItem(
                            id=item_id,
                            player_name=player_name,
                            from_club=team_out.get("name"),
                            to_club=team_in.get("name"),
                            fee=entry.get("type"),
                            transfer_type=entry.get("type"),
                            date=date,
                            source="API-Football",
                            url="https://www.api-football.com/",
                            summary=f"{player_name} moved from {team_out.get('name', '?')} to {team_in.get('name', '?')}",
                            image_url=team_in.get("logo"),
                        )
                    )

    transfers.sort(key=lambda t: t.date, reverse=True)
    return transfers[:limit]


async def fetch_transfer_items(*, limit: int = 30) -> list[TransferItem]:
    cache_key = "news:transfers:combined:v2"
    cached = _memory_get(cache_key)
    if cached is None:
        cached = await get_json_cached(cache_key)
    if cached is not None:
        return [
            TransferItem(
                **{
                    **item,
                    "image_url": _upgrade_image_url(item["image_url"])
                    if item.get("image_url")
                    else None,
                }
            )
            for item in cached[:limit]
        ]

    transfers: list[TransferItem] = []
    seen: set[str] = set()

    # Structured deals from API-Football when available.
    transfers.extend(await _fetch_api_transfers(limit=limit))

    # Real transfer news from RSS (Guardian transfer window + tagged articles).
    for feed, items in await _fetch_feeds(TRANSFER_FEEDS):
        for item in items:
            if item["link"] in seen:
                continue
            seen.add(item["link"])

            player, from_club, to_club, fee = _parse_transfer_from_text(
                item["title"], item["summary"]
            )
            image_url = item.get("image_url")
            if image_url:
                image_url = _upgrade_image_url(image_url)

            transfers.append(
                TransferItem(
                    id=_stable_id("transfer-news", item["link"]),
                    player_name=player,
                    from_club=from_club,
                    to_club=to_club,
                    fee=fee,
                    transfer_type=fee,
                    date=item["published_at"][:10],
                    source=feed["source"],
                    url=item["link"],
                    summary=item["summary"],
                    image_url=image_url,
                )
            )

    # Transfer-tagged headlines from main football feeds.
    for feed, items in await _fetch_feeds(NEWS_FEEDS):
        for item in items:
            blob = f"{item['title']} {item['summary']}".lower()
            if not any(k in blob for k in ("transfer", "signs", "signed", "deal", "joins", "loan")):
                continue
            if item["link"] in seen:
                continue
            seen.add(item["link"])

            player, from_club, to_club, fee = _parse_transfer_from_text(
                item["title"], item["summary"]
            )
            image_url = item.get("image_url")
            if image_url:
                image_url = _upgrade_image_url(image_url)

            transfers.append(
                TransferItem(
                    id=_stable_id("transfer-news", item["link"]),
                    player_name=player,
                    from_club=from_club,
                    to_club=to_club,
                    fee=fee,
                    transfer_type=fee,
                    date=item["published_at"][:10],
                    source=feed["source"],
                    url=item["link"],
                    summary=item["summary"],
                    image_url=image_url,
                )
            )

    transfers.sort(key=lambda t: t.date, reverse=True)
    serialized = [t.model_dump() for t in transfers[: max(limit, 60)]]
    _memory_set(cache_key, serialized, ttl_seconds=CACHE_TTL_TRANSFERS)
    await set_json_cached(cache_key, serialized, ttl_seconds=CACHE_TTL_TRANSFERS)
    return transfers[:limit]


async def get_news_feed(*, category: str | None = None, limit: int = 40) -> NewsFeedResponse:
    articles = await fetch_news_articles(category=category, limit=limit)
    transfers = await fetch_transfer_items(limit=min(limit, 30))

    return NewsFeedResponse(
        articles=articles,
        transfers=transfers,
        categories=NEWS_CATEGORIES,
    )
