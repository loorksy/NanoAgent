"""Regression: model-facing trading serializers stay compact (no pretty spaces)."""

from __future__ import annotations

import json

from mokli.trading.agents.evidence import evidence_json_for_model
from mokli.trading.agents.macro_drivers import MacroVerdict, format_team_briefing
from mokli.agent.tools import mt5_execution as mt5_exec_tools
from mokli.agent.tools import mt5_market as mt5_market_tools
from mokli.trading.capture_service import chart_capture_tool_result
from mokli.trading.tool_errors import model_json


def _is_compact_json(text: str) -> bool:
    parsed = json.loads(text)
    loose = json.dumps(parsed, ensure_ascii=False, default=str)
    return text == model_json(parsed) and len(text) <= len(loose)


def test_evidence_json_for_model_stays_compact() -> None:
    payload = {
        "evidenceLevels": [2290.0, 2300.0],
        "candidates": [{"id": "c1", "action": "wait"}],
        "teamBriefing": "- technical: range\nSTANCE: wait",
        "geometry": {"gaps": [{"low": 2298.5, "high": 2302.0}]},
    }
    text = evidence_json_for_model(payload)
    assert _is_compact_json(text)


def test_format_team_briefing_stays_compact() -> None:
    verdicts = [
        MacroVerdict(
            driver="dxy",
            bias="bearish",
            strength=2,
            one_line_rationale="dollar soft",
            source="web_search",
            ran=True,
            reason="cache_miss_slow",
        )
    ]
    text = format_team_briefing(verdicts)
    assert _is_compact_json(text)


def test_chart_capture_brief_stays_compact() -> None:
    text = chart_capture_tool_result({"ok": True, "interval": "15m", "chartSnapshots": []})
    assert _is_compact_json(text)
    assert "data:image" not in text


def test_mt5_tool_json_helpers_stay_compact() -> None:
    market = mt5_market_tools._json({"ok": True, "symbol": "XAUUSD", "bid": 2301.2})
    execution = mt5_exec_tools._json({"ok": False, "reason_key": "trading.policy_violation"})
    assert _is_compact_json(market)
    assert _is_compact_json(execution)
