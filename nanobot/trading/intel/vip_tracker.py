"""FEATURE-03 — VIP / central-bank statement tracker via public Nitter RSS (no X API)."""

from __future__ import annotations

from dataclasses import dataclass

from nanobot.trading.intel.rss_aggregator import fetch_rss_headlines

DEFAULT_HANDLES = (
    "federalreserve",
    "ecb",
    "bankofengland",
    "USTreasury",
)

# Public Nitter instances (best-effort; callers may override).
DEFAULT_NITTER_HOSTS = (
    "https://nitter.net",
    "https://nitter.privacydev.net",
)


@dataclass(frozen=True)
class VipStatement:
    handle: str
    text: str
    impact: str
    guid: str
    link: str = ""


def _impact(handle: str) -> str:
    high = {"federalreserve", "ecb", "USTreasury", "bankofengland", "Lagarde", "federalreserve"}
    return "high" if handle.lstrip("@") in high else "medium"


async def fetch_vip_statements(
    handles: tuple[str, ...] | list[str] = DEFAULT_HANDLES,
    *,
    hosts: tuple[str, ...] = DEFAULT_NITTER_HOSTS,
) -> list[VipStatement]:
    feeds: list[str] = []
    host = hosts[0]
    for handle in handles:
        feeds.append(f"{host}/{handle.lstrip('@')}/rss")
    headlines = await fetch_rss_headlines(feeds)
    out: list[VipStatement] = []
    for item in headlines:
        handle = item.feed.rsplit("/", 2)[-2] if "/" in item.feed else "unknown"
        out.append(
            VipStatement(
                handle=handle,
                text=item.title,
                impact=_impact(handle),
                guid=item.guid,
                link=item.link,
            )
        )
    return out
