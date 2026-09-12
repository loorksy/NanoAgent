"""Phase 3: macroDrivers must change synthesizer confidence inside the unified agent.

STOP A: before the documented adjustment rule, opposite briefings produced the
same confidence because teamBriefing was only dumped into evidence JSON.
"""

from __future__ import annotations

import json

import pytest

from nanobot.trading.agents.apply_model_decision import (
    MACRO_CONFIDENCE_WEIGHT,
    apply_macro_confidence,
    apply_model_decision,
    macro_alignment_score,
    parse_macro_drivers,
)
from nanobot.trading.agents.macro_drivers import format_team_briefing
from nanobot.trading.agents.synth_prompt import SYNTH_SYSTEM_PROMPT
from nanobot.trading.orchestrator import run_unified_chart_agent
from nanobot.trading.types import (
    AgentMarketContext,
    Candle,
    EvidenceSnapshot,
    GateChainResult,
    LiquidityResult,
    MarketSync,
    MultiTimeframeResult,
    NewsMacroResult,
    RiskAgentResult,
    StructureResult,
    SupplyDemandResult,
    TradeCandidate,
    TradeValidationResult,
    VisualReview,
)


def _driver(name: str, bias: str, strength: int) -> dict:
    from nanobot.trading.agents.macro_drivers import MacroVerdict

    return MacroVerdict(
        driver=name,
        bias=bias,
        strength=strength,
        one_line_rationale=f"{name} {bias}",
        source="Reuters",
        ran=True,
        reason="cache_miss",
    )


def _briefing(bias: str, strength: int = 80) -> str:
    return format_team_briefing(
        [
            _driver("dxy", bias, strength),
            _driver("geopolitical_safehaven", bias, strength),
            _driver("us_real_yields_fomc", bias, strength),
        ]
    )


def _fixed_model_json() -> str:
    return json.dumps(
        {
            "direction": "buy",
            "planType": "immediate",
            "selectedTradeCandidateId": "cand-bull-1",
            "proposedLevels": None,
            "confidence": 0.60,
            "summary": "Gold BUY from demand",
            "keyReasons": ["demand held"],
            "riskWarnings": [],
            "decisionTrace": {
                "hypotheses": [{"scenario": "buy", "supporting": ["demand"], "opposing": []}],
                "chosenBecause": "demand",
                "planTypeBecause": "inside zone",
            },
            "scenarioPath": [
                {"barsAhead": 2, "price": 2410, "label": "impulse"},
                {"barsAhead": 8, "price": 2440, "label": "target"},
            ],
            "alternativeScenarioPath": [
                {"barsAhead": 3, "price": 2392, "label": "fail"},
                {"barsAhead": 6, "price": 2385, "label": "stop"},
            ],
            "browse": None,
        }
    )


def _snapshot(briefing: str | None) -> EvidenceSnapshot:
    return EvidenceSnapshot(
        payload={
            "mtf": {"current_bias": "bullish", "conflict": False},
            "structure": {"trend": "uptrend"},
            "candidates": [
                {
                    "id": "cand-bull-1",
                    "action": "buy",
                    "entry": 2400.0,
                    "stopLoss": 2385.0,
                    "targets": [2420.0, 2440.0],
                    "entryType": "market",
                }
            ],
            "teamBriefing": briefing,
        },
        evidence_levels=[2385.0, 2400.0, 2420.0, 2440.0],
    )


def test_prompt_names_macro_briefing() -> None:
    assert "teamBriefing.macroDrivers" in SYNTH_SYSTEM_PROMPT
    assert "raise confidence" in SYNTH_SYSTEM_PROMPT


def test_opposite_briefings_change_apply_model_confidence() -> None:
    parsed = json.loads(_fixed_model_json())
    bull = apply_model_decision(
        parsed, snapshot=_snapshot(_briefing("bullish")), live_price=2400.0, atr=8.0, locale="en"
    )
    bear = apply_model_decision(
        parsed, snapshot=_snapshot(_briefing("bearish")), live_price=2400.0, atr=8.0, locale="en"
    )
    none = apply_model_decision(
        parsed, snapshot=_snapshot(None), live_price=2400.0, atr=8.0, locale="en"
    )
    # Same model JSON: side stays buy; confidence must move.
    assert bull.decision == bear.decision == "buy"
    assert none.confidence == pytest.approx(0.60)
    assert bull.confidence == pytest.approx(apply_macro_confidence(0.60, 1.0))
    assert bear.confidence == pytest.approx(apply_macro_confidence(0.60, -1.0))
    assert bull.confidence - bear.confidence == pytest.approx(2 * MACRO_CONFIDENCE_WEIGHT)
    assert any("Macro drivers" in reason for reason in bull.key_reasons)


def test_parse_and_alignment_helpers() -> None:
    drivers = parse_macro_drivers(_snapshot(_briefing("bearish")))
    assert len(drivers) == 3
    assert macro_alignment_score("buy", drivers) == pytest.approx(-1.0)
    assert macro_alignment_score("sell", drivers) == pytest.approx(1.0)


def _fake_market() -> AgentMarketContext:
    return AgentMarketContext(
        symbol="XAUUSD",
        interval="15m",
        candles=[Candle(i, 2395, 2410, 2390, 2400, 1) for i in range(20)],
        last_close=2400.0,
        atr=8.0,
        sync=MarketSync(ok=True),
        quote_mid=2400.0,
    )


def _install_specialist_stubs(monkeypatch) -> None:
    market = _fake_market()
    structure = StructureResult("uptrend", [], [], [], [])
    liquidity = LiquidityResult([], [], None, None, [], None)
    supply = SupplyDemandResult([], None, None)
    mtf = MultiTimeframeResult("bullish", "bullish", "bullish", False)
    news = NewsMacroResult("low", "unknown", [], [], True, "")
    buy = TradeCandidate("cand-bull-1", "buy", 2400, "market", 2385, [2420, 2440], 2.0, 0.8)
    sell = TradeCandidate("cand-bear-1", "sell", 2400, "market", 2415, [2380, 2360], 2.0, 0.4)
    risk = RiskAgentResult(
        proposed_trade=buy,
        validation=TradeValidationResult(accepted=True, reasons=[]),
        selected_candidate=buy,
        candidates=[buy, sell],
    )
    allowed = GateChainResult(verdicts=[], allowed=True, confidence_delta=0)

    async def _allowed(*_a, **_k):
        return allowed

    monkeypatch.setattr("nanobot.trading.orchestrator.run_market_data_agent", lambda *_a, **_k: market)
    monkeypatch.setattr("nanobot.trading.orchestrator.run_structure_agent", lambda *_a, **_k: structure)
    monkeypatch.setattr("nanobot.trading.orchestrator.run_liquidity_agent", lambda *_a, **_k: liquidity)
    monkeypatch.setattr("nanobot.trading.orchestrator.run_supply_demand_agent", lambda *_a, **_k: supply)
    monkeypatch.setattr("nanobot.trading.orchestrator.run_multi_timeframe_agent", lambda *_a, **_k: mtf)
    monkeypatch.setattr("nanobot.trading.orchestrator.run_news_macro_agent", lambda *_a, **_k: news)
    monkeypatch.setattr("nanobot.trading.orchestrator.run_risk_agent", lambda *_a, **_k: risk)
    monkeypatch.setattr("nanobot.trading.orchestrator.run_gate_chain", _allowed)

    async def _no_reprice(chain, gates, plan, rec):
        return chain, plan, rec

    monkeypatch.setattr(
        "nanobot.trading.gates.reprice_loop.apply_g7_reprice_loop",
        _no_reprice,
    )


@pytest.mark.asyncio
async def test_unified_agent_opposite_briefings_change_confidence(monkeypatch) -> None:
    _install_specialist_stubs(monkeypatch)
    seen: list[str] = []

    async def complete(messages):
        blob = json.dumps(messages, default=str)
        seen.append(blob)
        assert "teamBriefing" in blob
        assert "macroDrivers" in blob
        return _fixed_model_json()

    async def visual(_interval, capture=None):
        return VisualReview(state="not_checked"), []

    monkeypatch.setattr("nanobot.trading.orchestrator.capture_visual_evidence", visual)

    bull = await run_unified_chart_agent(
        store=False,
        team_briefing=_briefing("bullish"),
        complete=complete,
    )
    bear = await run_unified_chart_agent(
        store=False,
        team_briefing=_briefing("bearish"),
        complete=complete,
    )
    assert bull.decision.decision == "buy"
    assert bear.decision.decision == "buy"
    assert bull.decision.confidence > bear.decision.confidence
    assert bull.decision.confidence - bear.decision.confidence == pytest.approx(
        2 * MACRO_CONFIDENCE_WEIGHT
    )
    assert any("teamBriefing" in blob for blob in seen)
