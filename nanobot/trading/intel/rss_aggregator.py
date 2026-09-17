"""FEATURE-02 — async RSS aggregator (aiohttp + feedparser, with httpx fallback)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from nanobot.trading.intel.optional_deps import module_available

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
    body_by_url: dict[str, str] = {}
    if module_available("aiohttp"):
        import aiohttp

        async with aiohttp.ClientSession() as session:
            for url in feeds:
                try:
                    async with session.get(url, timeout=timeout) as resp:
                        body_by_url[url] = await resp.text()
                except Exception:
                    continue
        return body_by_url
    import httpx

    async with httpx.AsyncClient(timeout=timeout) as client:
        for url in feeds:
            try:
                resp = await client.get(url)
                body_by_url[url] = resp.text
            except Exception:
                continue
    return body_by_url


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
