"""Macro-driver selection, cache TTL, and swarm briefing — no live web search."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from nanobot.trading.agents.macro_drivers import (
    DRIVER_DXY,
    DRIVER_GEOPOLITICAL,
    DRIVER_SEASONAL,
    DRIVER_US_REAL_YIELDS_FOMC,
    format_team_briefing,
    reset_macro_cache_for_tests,
    run_macro_drivers,
    select_drivers,
)
from nanobot.trading.result_wire import result_to_wire
from nanobot.trading.teams.runtime import run_swarm
from nanobot.trading.types import AgentFinalResult, AgentRecommendation, FinalDecisionResult


def _friday_ts() -> float:
    return datetime(2026, 9, 11, 16, 0, tzinfo=UTC).timestamp()  # Friday


def _wednesday_january_ts() -> float:
    return datetime(2026, 1, 7, 12, 0, tzinfo=UTC).timestamp()  # Wednesday, CNY window


def test_select_skips_fresh_cache_unless_calendar_hits() -> None:
    reset_macro_cache_for_tests()
    now = _friday_ts()
    cache: dict = {}
    first = select_drivers(events=[], now_ts=now, cache=cache)
    names = {name for name, _reason in first}
    assert DRIVER_GEOPOLITICAL in names
    assert DRIVER_DXY in names

    from nanobot.trading.agents.macro_drivers import MacroVerdict

    cache[DRIVER_GEOPOLITICAL] = (
        now,
        MacroVerdict(
            driver=DRIVER_GEOPOLITICAL,
            bias="bullish",
            strength=70,
            one_line_rationale="cached",
            source="web_search",
            ran=True,
            reason="cache_miss",
        ),
    )
    second = select_drivers(events=[], now_ts=now + 60, cache=cache)
    assert DRIVER_GEOPOLITICAL not in {name for name, _ in second}

    forced = select_drivers(
        events=[{"title": "FOMC Rate Decision", "impact": "high"}],
        now_ts=now + 60,
        cache=cache,
    )
    assert any(name == DRIVER_US_REAL_YIELDS_FOMC for name, _reason in forced)


def test_seasonal_only_in_festival_months() -> None:
    reset_macro_cache_for_tests()
    july = datetime(2026, 7, 8, 12, 0, tzinfo=UTC).timestamp()
    selected_july = select_drivers(events=[], now_ts=july, cache={})
    assert DRIVER_SEASONAL not in {name for name, _ in selected_july}

    jan = _wednesday_january_ts()
    selected_jan = select_drivers(events=[], now_ts=jan, cache={})
    assert DRIVER_SEASONAL in {name for name, _ in selected_jan}


@pytest.mark.asyncio
async def test_run_macro_drivers_uses_injected_search() -> None:
    reset_macro_cache_for_tests()
    queries: list[str] = []

    async def search(query: str) -> str:
        queries.append(query)
        return "Gold rises on weaker dollar and dovish FOMC"

    verdicts = await run_macro_drivers(
        search=search,
        events=[],
        now=_friday_ts,
        cache={},
    )
    ran = [item for item in verdicts if item.ran]
    assert ran
    assert queries
    assert all(item.source == "web_search" for item in ran)
    assert any(item.bias == "bullish" for item in ran)
    briefing = format_team_briefing(verdicts)
    assert "macroDrivers" in briefing
    assert DRIVER_DXY in briefing or DRIVER_GEOPOLITICAL in briefing


@pytest.mark.asyncio
async def test_run_swarm_feeds_briefing_and_keeps_unified_pipeline(monkeypatch) -> None:
    reset_macro_cache_for_tests()
    captured: dict[str, object] = {}

    async def fake_chart_agent(**kwargs):
        captured.update(kwargs)
        return AgentFinalResult(
            decision=FinalDecisionResult(
                decision="wait",
                confidence=0.0,
                summary="stub",
                key_reasons=[],
                risk_warnings=[],
                recommendation=AgentRecommendation(action="wait"),
            ),
            team_mode=str(kwargs.get("team_mode") or ""),
            stages=[],
        )

    async def search(query: str) -> str:
        return "DXY falling, gold ETF inflows, PBOC buying"

    monkeypatch.setattr(
        "nanobot.trading.teams.runtime.run_unified_chart_agent",
        fake_chart_agent,
    )
    swarm = await run_swarm(
        "gold_analysis_committee",
        macro_search=search,
        macro_events=[],
        macro_now=_friday_ts,
    )
    assert captured["team_mode"] == "swarm:gold_analysis_committee"
    assert captured["team_briefing"]
    assert "macroDrivers" in str(captured["team_briefing"])
    final = swarm["final"]
    assert final.macro_drivers
    assert any(stage.get("stage") == "macro_drivers" for stage in final.stages)
    wire = result_to_wire(final)
    assert wire["macroDrivers"]
    assert wire["teamMode"] == "swarm:gold_analysis_committee"
    # YAML DAG still recorded; it does not replace the unified agent.
    assert swarm["task_summaries"]
