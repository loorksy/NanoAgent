"""FEATURE-02 — async RSS aggregator (aiohttp + feedparser, with httpx fallback)."""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass

from mokli.trading.intel.optional_deps import module_available

DEFAULT_FEEDS = (
    "https://www.federalreserve.gov/feeds/press_all.xml",
    "https://feeds.reuters.com/reuters/businessNews",
    "https://feeds.apnews.com/apf-topnews",
)

_SEEN: set[str] = set()


@dataclass(frozen=True)
class RssHeadline:
    feed: str
    title: str
    summary: str
    guid: str
    link: str = ""


def rss_backend() -> str:
    if not module_available("feedparser"):
        return "unavailable"
    if module_available("aiohttp"):
        return "aiohttp_feedparser"
    return "httpx_feedparser"


def _guid(entry: dict[str, str], feed: str) -> str:
    raw = entry.get("id") or entry.get("guid") or entry.get("link") or entry.get("title") or ""
    if raw:
        return str(raw)
    return hashlib.sha1(f"{feed}|{entry.get('title', '')}".encode()).hexdigest()


async def _fetch_bodies(feeds: tuple[str, ...] | list[str], timeout: float) -> dict[str, str]:
    """Download independent feeds together. Failures stay missing."""
    urls = tuple(feeds)

    def _remember(pairs: list[tuple[str, str | None]]) -> dict[str, str]:
        bodies: dict[str, str] = {}
        for url, body in pairs:
            if body is not None:
                bodies[url] = body
        return bodies

    if module_available("aiohttp"):
        import aiohttp

        async def _aiohttp_one(session: aiohttp.ClientSession, url: str) -> tuple[str, str | None]:
            try:
                async with session.get(url, timeout=timeout) as resp:
                    return url, await resp.text()
            except Exception:
                return url, None

        async with aiohttp.ClientSession() as session:
            pairs = await asyncio.gather(*[_aiohttp_one(session, url) for url in urls])
        return _remember(list(pairs))

    import httpx

    async def _httpx_one(client: httpx.AsyncClient, url: str) -> tuple[str, str | None]:
        try:
            resp = await client.get(url)
            return url, resp.text
        except Exception:
            return url, None

    async with httpx.AsyncClient(timeout=timeout) as client:
        pairs = await asyncio.gather(*[_httpx_one(client, url) for url in urls])
    return _remember(list(pairs))


async def fetch_rss_headlines(
    feeds: tuple[str, ...] | list[str] = DEFAULT_FEEDS,
    *,
    timeout: float = 8.0,
) -> list[RssHeadline]:
    if not module_available("feedparser"):
        return []
    items: list[RssHeadline] = []
    body_by_url = await _fetch_bodies(feeds, timeout)
    for url, body in body_by_url.items():
        items.extend(parse_feed_body(url, body))
    return items


def parse_feed_body(url: str, body: str) -> list[RssHeadline]:
    if not module_available("feedparser"):
        return []
    import feedparser

    items: list[RssHeadline] = []
    parsed = feedparser.parse(body)
    for entry in parsed.entries:
        mapping = {
            "id": str(getattr(entry, "id", "") or ""),
            "guid": str(getattr(entry, "guid", "") or ""),
            "link": str(getattr(entry, "link", "") or ""),
            "title": str(getattr(entry, "title", "") or ""),
        }
        gid = _guid(mapping, url)
        if gid in _SEEN:
            continue
        _SEEN.add(gid)
        items.append(
            RssHeadline(
                feed=url,
                title=mapping["title"],
                summary=str(getattr(entry, "summary", "") or ""),
                guid=gid,
                link=mapping["link"],
            )
        )
    return items


def reset_seen_for_tests() -> None:
    _SEEN.clear()
