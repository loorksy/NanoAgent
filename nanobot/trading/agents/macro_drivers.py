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

    if not _cached_fresh(DRIVER_SEASONAL) and _in_festival_window(now):
        selected.append((DRIVER_SEASONAL, "festival_window"))

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


def _verdict_from_snippets(driver: str, snippets: str, reason: str) -> MacroVerdict:
    bias, strength = _bias_from_text(snippets)
    one_line = re.sub(r"\s+", " ", snippets).strip()[:220] or "No usable snippets."
    return MacroVerdict(
        driver=driver,
        bias=bias,
        strength=strength,
        one_line_rationale=one_line,
        source="web_search",
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
