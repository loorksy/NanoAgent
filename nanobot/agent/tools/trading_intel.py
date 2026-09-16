"""Gold intelligence tools — FEATURE-01..10 free engines (opt-in extras)."""

from __future__ import annotations

import json
from typing import Any

from nanobot.agent.tools.base import Tool
from nanobot.agent.tools.schema import StringSchema, tool_parameters_schema
from nanobot.trading.intel.calendar_scraper import fetch_economic_calendar
from nanobot.trading.intel.dtw_matcher import match_pattern
from nanobot.trading.intel.intermarket import intermarket_snapshot
from nanobot.trading.intel.local_sentiment import classify_sentiment
from nanobot.trading.intel.postmortem import PostMortemLog
from nanobot.trading.intel.regex_emergency import scan_emergency
from nanobot.trading.intel.rss_aggregator import fetch_rss_headlines
from nanobot.trading.intel.vector_playbook import VectorPlaybook
from nanobot.trading.intel.vip_tracker import fetch_vip_statements


def _json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


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
        headlines = await fetch_rss_headlines()
        vips = await fetch_vip_statements()
        calendar = await fetch_economic_calendar()
        emergency = scan_emergency(text, apply_lock=bool(text))
        sentiment = await classify_sentiment(text or " ".join(h.title for h in headlines[:5]))
        playbook = VectorPlaybook().query(context or text or "gold london sweep")
        series = [float(x) for x in closes.split(",") if x.strip()] if closes else []
        pattern = match_pattern(series).name if series else "skipped"
        losses = PostMortemLog().recent_losses(3)
        market = intermarket_snapshot()
        return _json(
            {
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
                "playbook": [{"scenario": m.scenario, "score": m.score} for m in playbook],
                "pattern": pattern,
                "recent_losses": len(losses),
                "intermarket": market.prices,
            }
        )
