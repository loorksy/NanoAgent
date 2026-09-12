"""Conditional gold macro-driver specialists for swarm mode.

Each driver returns a small structured verdict. Evidence comes from the
existing web_search tool (DuckDuckGo by default — no new paid news API).

Seasonal physical demand (India/China festival windows, refinery trade)
has no clean free API; comments below say so explicitly instead of faking
a data source. COT/WGC prints are also located via web search snippets.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any, Awaitable, Callable
from urllib.parse import urlparse

from loguru import logger

from nanobot.trading.news.forex_factory import fetch_upcoming_events

SearchFn = Callable[[str], Awaitable[str]]
NowFn = Callable[[], float]

DRIVER_US_REAL_YIELDS_FOMC = "us_real_yields_fomc"
DRIVER_DXY = "dxy"
DRIVER_US_MACRO_DATA = "us_macro_data"
DRIVER_GEOPOLITICAL = "geopolitical_safehaven"
DRIVER_CENTRAL_BANK = "central_bank_demand"
DRIVER_FUND_FLOWS = "fund_flows_positioning"
DRIVER_SEASONAL = "seasonal_physical_demand"

# Fast news vs slow prints. Values are seconds.
TTL_SECONDS: dict[str, int] = {
    DRIVER_GEOPOLITICAL: 15 * 60,
    DRIVER_DXY: 30 * 60,
    DRIVER_US_REAL_YIELDS_FOMC: 30 * 60,
    DRIVER_US_MACRO_DATA: 60 * 60,
    DRIVER_FUND_FLOWS: 12 * 60 * 60,
    DRIVER_CENTRAL_BANK: 24 * 60 * 60,
    DRIVER_SEASONAL: 24 * 60 * 60,
}

CALENDAR_KEYWORDS: dict[str, tuple[str, ...]] = {
    DRIVER_US_REAL_YIELDS_FOMC: ("fomc", "fed", "federal reserve", "interest rate", "dot plot", "tips"),
    DRIVER_DXY: ("usd", "dollar", "dxy", "fomc", "cpi"),
    DRIVER_US_MACRO_DATA: (
        "nfp",
        "nonfarm",
        "unemployment",
        "cpi",
        "pce",
        "ppi",
        "retail sales",
        "payroll",
    ),
}

SEARCH_QUERIES: dict[str, str] = {
    DRIVER_US_REAL_YIELDS_FOMC: "US 10 year TIPS real yield FOMC stance gold",
    DRIVER_DXY: "DXY US dollar index trend today gold",
    DRIVER_US_MACRO_DATA: "US NFP CPI Core PCE PPI retail sales surprise vs consensus",
    DRIVER_GEOPOLITICAL: "geopolitical risk safe haven gold war sanctions banking stress",
    DRIVER_CENTRAL_BANK: "PBOC central bank gold buying World Gold Council quarterly",
    DRIVER_FUND_FLOWS: "CFTC COT gold futures speculators GLD ETF flows Friday",
    # No clean free API for festival/refinery physical demand — web search only.
    DRIVER_SEASONAL: "India China gold festival demand Diwali Akshaya Tritiya imports",
}

_BULLISH = (
    "bullish",
    "rises",
    "rising",
    "higher",
    "buying",
    "inflow",
    "safe haven bid",
    "weaker dollar",
    "dovish",
    "surprise beat",
)
_BEARISH = (
    "bearish",
    "falls",
    "falling",
    "lower",
    "selling",
    "outflow",
    "stronger dollar",
    "hawkish",
    "miss",
    "risk-on",
)

_CACHE: dict[str, tuple[float, "MacroVerdict"]] = {}


@dataclass(frozen=True)
class MacroVerdict:
    driver: str
    bias: str
    strength: int
    one_line_rationale: str
    source: str
    ran: bool
    reason: str

    def to_wire(self) -> dict[str, Any]:
        return asdict(self)


def reset_macro_cache_for_tests() -> None:
    _CACHE.clear()


def _clamp_strength(value: int) -> int:
    return max(0, min(100, value))


def _bias_from_text(text: str) -> tuple[str, int]:
    lowered = text.lower()
    bull = sum(1 for token in _BULLISH if token in lowered)
    bear = sum(1 for token in _BEARISH if token in lowered)
    if bull == bear:
        return "neutral", 35 if bull == 0 else 50
    if bull > bear:
        return "bullish", _clamp_strength(45 + 10 * (bull - bear))
    return "bearish", _clamp_strength(45 + 10 * (bear - bull))


def _event_matches(event: dict[str, Any], keywords: tuple[str, ...]) -> bool:
    blob = " ".join(
        str(event.get(key) or "") for key in ("title", "event", "currency", "country")
    ).lower()
    return any(keyword in blob for keyword in keywords)


def calendar_hits(
    events: list[dict[str, Any]],
    driver: str,
) -> list[dict[str, Any]]:
    keywords = CALENDAR_KEYWORDS.get(driver)
    if not keywords:
        return []
    return [event for event in events if _event_matches(event, keywords)]


def _in_festival_window(now: datetime) -> bool:
    """Best-effort seasonal windows. Not a data API — month-only heuristic."""
    month = now.month
    # Chinese New Year demand (Jan–Feb), Akshaya Tritiya (Apr–May), Diwali (Oct–Nov).
    return month in {1, 2, 4, 5, 10, 11}


def _is_cot_window(now: datetime) -> bool:
    # CFTC COT is published Fridays (US). Weekend still treats the print as fresh.
    return now.weekday() >= 4


def select_drivers(
    *,
    events: list[dict[str, Any]],
    now_ts: float,
    cache: dict[str, tuple[float, MacroVerdict]] | None = None,
) -> list[tuple[str, str]]:
    """Return (driver, why) pairs that should run now."""
    store = _CACHE if cache is None else cache
    now = datetime.fromtimestamp(now_ts, tz=UTC)
    selected: list[tuple[str, str]] = []

    def _cached_fresh(name: str) -> bool:
        row = store.get(name)
        if row is None:
            return False
        return (now_ts - row[0]) < TTL_SECONDS[name]

    always_on_miss = (DRIVER_GEOPOLITICAL, DRIVER_DXY, DRIVER_US_MACRO_DATA)
    for name in always_on_miss:
        hits = calendar_hits(events, name)
        if hits:
            selected.append((name, f"calendar:{hits[0].get('title') or hits[0].get('event') or name}"))
            continue
        if _cached_fresh(name):
            continue
        selected.append((name, "cache_miss"))

    if not _cached_fresh(DRIVER_US_REAL_YIELDS_FOMC):
        hits = calendar_hits(events, DRIVER_US_REAL_YIELDS_FOMC)
        if hits:
            selected.append(
                (DRIVER_US_REAL_YIELDS_FOMC, f"calendar:{hits[0].get('title') or 'FOMC'}")
            )
        else:
            selected.append((DRIVER_US_REAL_YIELDS_FOMC, "cache_miss"))
    elif calendar_hits(events, DRIVER_US_REAL_YIELDS_FOMC):
        selected.append((DRIVER_US_REAL_YIELDS_FOMC, "calendar_refresh"))

    if not _cached_fresh(DRIVER_FUND_FLOWS) and _is_cot_window(now):
        selected.append((DRIVER_FUND_FLOWS, "cot_window"))
    elif not _cached_fresh(DRIVER_FUND_FLOWS):
        selected.append((DRIVER_FUND_FLOWS, "cache_miss_slow"))

    if not _cached_fresh(DRIVER_CENTRAL_BANK):
        selected.append((DRIVER_CENTRAL_BANK, "cache_miss_slow"))

    # seasonal_physical_demand is intentionally not in the default set.
    # There is no clean free API; the month heuristic + generic festival
    # search produced always-neutral landing-page copy in live traces.

    # Deduplicate while keeping first reason.
    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for name, reason in selected:
        if name in seen:
            continue
        seen.add(name)
        unique.append((name, reason))
    return unique


def format_team_briefing(verdicts: list[MacroVerdict]) -> str:
    payload = [item.to_wire() for item in verdicts]
    return json.dumps({"macroDrivers": payload}, ensure_ascii=False)


_RESULT_RE = re.compile(
    r"(?m)^(?P<n>\d+)\.\s+(?P<title>.+?)\n[ \t]+(?P<url>https?://\S+)?(?:\n[ \t]+(?P<snippet>.+))?"
)
_BLOCKED_HOSTS = frozenset(
    {
        "twitter.com",
        "www.twitter.com",
        "mobile.twitter.com",
        "x.com",
        "www.x.com",
        "t.co",
    }
)
_JUNK_HOSTS = frozenset(
    {
        "watchgold.org",
        "www.watchgold.org",
    }
)
_JUNK_TITLE_MARKERS = (
    "live correlation chart",
    "live chart |",
    "— live correlation",
)
_OUTLET_ALIASES = {
    "reuters.com": "Reuters",
    "bloomberg.com": "Bloomberg",
    "ft.com": "Financial Times",
    "wsj.com": "WSJ",
    "cnbc.com": "CNBC",
    "marketwatch.com": "MarketWatch",
    "investing.com": "Investing.com",
    "kitco.com": "Kitco",
    "gold.org": "World Gold Council",
    "federalreserve.gov": "Federal Reserve",
    "bls.gov": "BLS",
    "cftc.gov": "CFTC",
    "lseg.com": "LSEG",
    "cmegroup.com": "CME",
}


def _host_from_url(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except ValueError:
        return ""


def _root_host(host: str) -> str:
    host = host.removeprefix("www.")
    parts = host.split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host


def outlet_from_url(url: str, title: str = "") -> str:
    """Named outlet or host from a result URL. Never Twitter/X."""
    host = _host_from_url(url)
    if not host:
        return (title.split("—")[0].split("|")[0].strip()[:48] or "web_search")
    if host in _BLOCKED_HOSTS or _root_host(host) in {"twitter.com", "x.com", "t.co"}:
        return ""
    alias = _OUTLET_ALIASES.get(host) or _OUTLET_ALIASES.get(_root_host(host))
    if alias:
        return alias
    return _root_host(host) or host


def parse_web_search_results(text: str) -> list[dict[str, str]]:
    """Parse titles/URLs/snippets from WebSearchTool plaintext output."""
    rows: list[dict[str, str]] = []
    for match in _RESULT_RE.finditer(text or ""):
        title = (match.group("title") or "").strip()
        url = (match.group("url") or "").strip()
        snippet = (match.group("snippet") or "").strip()
        if not title and not url:
            continue
        rows.append({"title": title, "url": url, "snippet": snippet})
    if rows:
        return rows
    # Injected tests may pass a single prose blob with no numbered hits.
    blob = re.sub(r"\s+", " ", (text or "").strip())
    if blob and not blob.lower().startswith("results for:"):
        return [{"title": "", "url": "", "snippet": blob}]
    return []


def _is_junk_result(item: dict[str, str]) -> bool:
    host = _host_from_url(item.get("url") or "")
    if host in _BLOCKED_HOSTS or _root_host(host) in {"twitter.com", "x.com", "t.co"}:
        return True
    if host in _JUNK_HOSTS:
        return True
    title = (item.get("title") or "").lower()
    return any(marker in title for marker in _JUNK_TITLE_MARKERS)


def _usable_results(text: str) -> list[dict[str, str]]:
    parsed = parse_web_search_results(text)
    kept = [item for item in parsed if not _is_junk_result(item)]
    return kept or [item for item in parsed if _host_from_url(item.get("url") or "") not in _BLOCKED_HOSTS]


def _verdict_from_snippets(driver: str, snippets: str, reason: str) -> MacroVerdict:
    kept = _usable_results(snippets)
    scored_text = " ".join(
        f"{item.get('title') or ''} {item.get('snippet') or ''}" for item in kept[:4]
    )
    bias, strength = _bias_from_text(scored_text)
    if not kept:
        return MacroVerdict(
            driver=driver,
            bias="neutral",
            strength=0,
            one_line_rationale="No usable non-social search hits.",
            source="web_search",
            ran=True,
            reason=f"{reason}:no_usable_snippets",
        )

    best = kept[0]
    outlet = outlet_from_url(best.get("url") or "", best.get("title") or "")
    source = (best.get("url") or "").strip() or outlet or "web_search"
    sentence = (best.get("snippet") or best.get("title") or "").strip()
    sentence = re.sub(r"\s+", " ", sentence)
    rationale = f"{outlet}: {sentence}".strip(": ").strip()[:220] if outlet else sentence[:220]
    if not rationale:
        rationale = "No usable snippets."
    # Chart-widget leftovers and equal-token ties stay weak.
    if bias == "neutral" and strength >= 50:
        strength = 25
    return MacroVerdict(
        driver=driver,
        bias=bias,
        strength=_clamp_strength(strength),
        one_line_rationale=rationale,
        source=source,
        ran=True,
        reason=reason,
    )


async def _default_search(query: str) -> str:
    from nanobot.agent.tools.web import WebSearchConfig, WebSearchTool

    tool = WebSearchTool(WebSearchConfig(provider="duckduckgo", max_results=5))
    return await tool.execute(query=query, count=5)


async def run_macro_drivers(
    *,
    search: SearchFn | None = None,
    events: list[dict[str, Any]] | None = None,
    now: NowFn | None = None,
    cache: dict[str, tuple[float, MacroVerdict]] | None = None,
) -> list[MacroVerdict]:
    """Run a relevance-filtered subset of macro specialists."""
    search_fn = search or _default_search
    now_fn = now or time.time
    store = _CACHE if cache is None else cache
    now_ts = now_fn()
    calendar = events if events is not None else fetch_upcoming_events()
    planned = select_drivers(events=calendar, now_ts=now_ts, cache=store)
    out: list[MacroVerdict] = []

    for name, why in planned:
        query = SEARCH_QUERIES[name]
        try:
            snippets = await search_fn(query)
        except Exception as exc:
            logger.warning("macro driver {} search failed: {}", name, exc)
            verdict = MacroVerdict(
                driver=name,
                bias="neutral",
                strength=0,
                one_line_rationale=f"web_search failed: {exc}",
                source="web_search",
                ran=True,
                reason=f"{why}:search_error",
            )
        else:
            verdict = _verdict_from_snippets(name, snippets or "", why)
        store[name] = (now_ts, verdict)
        out.append(verdict)
        logger.info(
            "macro driver ran driver={} reason={} bias={} strength={}",
            name,
            why,
            verdict.bias,
            verdict.strength,
        )

    # Surface still-fresh cached drivers so the synthesizer sees the full menu.
    ran = {item.driver for item in out}
    for name, (_ts, verdict) in store.items():
        if name not in ran:
            out.append(
                MacroVerdict(
                    driver=verdict.driver,
                    bias=verdict.bias,
                    strength=verdict.strength,
                    one_line_rationale=verdict.one_line_rationale,
                    source=verdict.source,
                    ran=False,
                    reason="cache_hit",
                )
            )
    return out
