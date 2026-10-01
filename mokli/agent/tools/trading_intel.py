"""Gold intelligence tools — FEATURE-01..10 free engines (opt-in extras)."""

from __future__ import annotations

import asyncio
from typing import Any

from mokli.agent.tools.base import Tool
from mokli.agent.tools.schema import StringSchema, tool_parameters_schema
from mokli.trading.intel.calendar_scraper import fetch_economic_calendar
from mokli.trading.intel.dtw_matcher import match_pattern
from mokli.trading.intel.intermarket import intermarket_snapshot
from mokli.trading.intel.local_sentiment import classify_sentiment
from mokli.trading.intel.postmortem import PostMortemLog
from mokli.trading.intel.regex_emergency import scan_emergency
from mokli.trading.intel.rss_aggregator import fetch_rss_headlines
from mokli.trading.intel.telegram_scraper import TelegramHeadlineSource
from mokli.trading.intel.vector_playbook import VectorPlaybook
from mokli.trading.intel.vip_tracker import fetch_vip_statements
from mokli.trading.tool_errors import model_json


def _json(payload: Any) -> str:
    return model_json(payload)


async def collect_intel_sources() -> tuple[Any, Any, Any, Any, TelegramHeadlineSource]:
    """RSS, VIP statements, the calendar, and Telegram are independent reads."""
    telegram = TelegramHeadlineSource()
    headlines, vips, calendar, telegram_rows = await asyncio.gather(
        fetch_rss_headlines(),
        fetch_vip_statements(),
        fetch_economic_calendar(),
        telegram.fetch_recent(),
    )
    return headlines, vips, calendar, telegram_rows, telegram


class GoldIntelScanTool(Tool):
    @property
    def name(self) -> str:
        return "gold_intel_scan"

    @property
    def description(self) -> str:
        return (
            "Run a free-tier gold intel scan: RSS headlines, VIP statements, economic calendar, "
            "regex emergency, local sentiment, vector playbook, DTW pattern, post-mortem, intermarket."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return tool_parameters_schema(
            text=StringSchema("Optional headline or speech text to classify"),
            context=StringSchema("Optional current setup description for playbook match"),
            closes=StringSchema("Optional comma-separated recent closes for DTW"),
            required=[],
        )

    @property
    def read_only(self) -> bool:
        return True

    async def execute(
        self,
        text: str = "",
        context: str = "",
        closes: str = "",
        **kwargs: Any,
    ) -> Any:
        del kwargs
        headlines, vips, calendar, telegram_rows, telegram = await collect_intel_sources()
        emergency = scan_emergency(text, apply_lock=bool(text))
        sentiment = await classify_sentiment(text or " ".join(h.title for h in headlines[:5]))
        book = VectorPlaybook()
        playbook = book.query(context or text or "gold london sweep")
        series = [float(x) for x in closes.split(",") if x.strip()] if closes else []
        pattern = match_pattern(series) if series else None
        losses = PostMortemLog().recent_losses(3)
        market = intermarket_snapshot()
        return _json(
            {
                "telegram": {
                    "available": telegram.available(),
                    "configured": telegram.configured(),
                    "backend": telegram.backend(),
                    "headlines": [row.text for row in telegram_rows],
                    "active": telegram.available(),
                },
                "rss": [h.title for h in headlines[:8]],
                "vip": [v.text for v in vips[:8]],
                "calendar": [c.title for c in calendar[:8]],
                "emergency": {
                    "matched": emergency.matched,
                    "category": emergency.category,
                    "freeze": emergency.freeze,
                },
                "sentiment": {
                    "bias": sentiment.bias,
                    "confidence": sentiment.confidence,
                    "source": sentiment.source,
                },
                "playbook": {
                    "backend": book.backend,
                    "matches": [{"scenario": m.scenario, "score": m.score} for m in playbook],
                },
                "pattern": (
                    None
                    if pattern is None
                    else {
                        "name": pattern.name,
                        "confidence": pattern.confidence,
                        "backend": pattern.backend,
                    }
                ),
                "recent_losses": len(losses),
                "intermarket": {
                    "prices": market.prices,
                    "source": market.source,
                    "active": bool(market.prices) and market.source not in {"none", "unavailable"},
                },
            }
        )
