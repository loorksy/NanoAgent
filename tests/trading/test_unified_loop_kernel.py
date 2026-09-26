"""Group A remaining kernel Hard Law tests + Group B loop behaviour."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from nanobot.agent.tools.trading_chart import GetGoldQuoteTool
from nanobot.trading.kernel import run_trading_kernel
from nanobot.trading.policy_guard import PolicyViolation
from nanobot.trading.recommendations.store import latest_live_recommendation, store_recommendation
from nanobot.trading.turn_session import TurnSession, turn_session_scope
from nanobot.trading.types import (
    AgentMarketContext,
    AgentRecommendation,
    FinalDecisionResult,
    GateChainResult,
    GateVerdict,
    MarketSync,
)
from nanobot.trading.unified_evidence import fetch_evidence_nodes
from tests.trading.evidence_stubs import fake_market, install_evidence_stubs


def _buy_decision() -> FinalDecisionResult:
    return FinalDecisionResult(
        decision="buy",
        confidence=0.8,
        summary="Buy gold",
        key_reasons=["structure"],
        risk_warnings=[],
        recommendation=AgentRecommendation(
            action="buy",
            entry=2400,
            stop_loss=2385,
            targets=[2420, 2440],
            execution_state="valid_now",
            interval="15m",
        ),
    )


def _seed_live(tmp_path, monkeypatch, session_key: str = "chat:unified") -> str:
    monkeypatch.setattr("nanobot.config.paths.get_data_dir", lambda: tmp_path)
    monkeypatch.setattr("nanobot.trading.recommendations.store.get_data_dir", lambda: tmp_path)
    market = AgentMarketContext(
        symbol="XAUUSD",
        interval="15m",
        candles=[],
        last_close=2400.0,
        atr=8.0,
        sync=MarketSync(ok=True),
    )
    rec_id = store_recommendation(
        FinalDecisionResult(
            decision="sell",
            confidence=0.7,
            summary="live sell",
            key_reasons=[],
            risk_warnings=[],
            recommendation=AgentRecommendation(
                action="sell",
                entry=2400,
                stop_loss=2415,
                targets=[2380, 2360],
                execution_state="valid_now",
            ),
        ),
        [],
        market,
        session_key=session_key,
    )
    assert rec_id
    return rec_id


@pytest.mark.asyncio
async def test_kernel_refuses_live_rec_without_force_new(tmp_path, monkeypatch) -> None:
    session_key = "chat:live-lock"
    _seed_live(tmp_path, monkeypatch, session_key)
    with turn_session_scope(TurnSession(session_key=session_key)):
        with pytest.raises(PolicyViolation, match="already has a live recommendation"):
            await run_trading_kernel(
                gather_missing=True,
                session_key=session_key,
                store=True,
            )
    assert latest_live_recommendation(session_key) is not None


@pytest.mark.asyncio
async def test_gate_veto_wait_never_flips_side(monkeypatch) -> None:
    install_evidence_stubs(monkeypatch, gate_allowed=False)
    veto = GateChainResult(
        verdicts=[],
        allowed=False,
        confidence_delta=-20,
        vetoed_by=GateVerdict(id="G4", name="structure", status="veto", reason="blocked"),
    )

    async def _synth(*_a, **_k):
        return _buy_decision()

    async def _chain(*_a, **_k):
        return veto

    async def _reprice(chain, gates, plan, rec):
        return chain, plan, rec

    monkeypatch.setattr("nanobot.trading.kernel.refuse_repeat_error", lambda **_k: None)
    monkeypatch.setattr("nanobot.trading.kernel.run_final_decision_synthesizer", _synth)
    monkeypatch.setattr("nanobot.trading.kernel.run_gate_chain", _chain)
    monkeypatch.setattr(
        "nanobot.trading.gates.reprice_loop.apply_g7_reprice_loop",
        _reprice,
    )
    monkeypatch.setattr("nanobot.trading.kernel.fetch_quote", lambda *_a, **_k: None)

    with turn_session_scope(TurnSession()):
        result = await run_trading_kernel(gather_missing=True, store=False, present_ui=False)
    assert result.decision.decision == "wait"
    assert result.decision.recommendation.action == "wait"
    assert result.decision.decision != "sell"
    assert result.recommendation_id in {None, ""}


@pytest.mark.asyncio
async def test_shadow_kernel_never_stores(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LONORA_UNIFIED_LOOP", "shadow")
    monkeypatch.setattr("nanobot.config.paths.get_data_dir", lambda: tmp_path)
    monkeypatch.setattr("nanobot.trading.recommendations.store.get_data_dir", lambda: tmp_path)
    install_evidence_stubs(monkeypatch, gate_allowed=True)

    async def _synth(*_a, **_k):
        return _buy_decision()

    async def _chain(*_a, **_k):
        return GateChainResult(verdicts=[], allowed=True, confidence_delta=0)

    async def _reprice(chain, gates, plan, rec):
        return chain, plan, rec

    monkeypatch.setattr("nanobot.trading.kernel.refuse_repeat_error", lambda **_k: None)
    monkeypatch.setattr("nanobot.trading.kernel.run_final_decision_synthesizer", _synth)
    monkeypatch.setattr("nanobot.trading.kernel.run_gate_chain", _chain)
    monkeypatch.setattr(
        "nanobot.trading.gates.reprice_loop.apply_g7_reprice_loop",
        _reprice,
    )
    monkeypatch.setattr("nanobot.trading.kernel.fetch_quote", lambda *_a, **_k: None)

    with turn_session_scope(TurnSession(session_key="chat:shadow")):
        result = await run_trading_kernel(
            gather_missing=True,
            store=True,
            session_key="chat:shadow",
            present_ui=False,
        )
    assert result.recommendation_id in {None, ""}
    assert latest_live_recommendation("chat:shadow") is None


@pytest.mark.asyncio
async def test_pipeline_context_shared_across_fetch_evidence_calls(monkeypatch) -> None:
    market = fake_market()
    calls = {"market": 0}

    def _market(_symbol, _interval):
        calls["market"] += 1
        return market

    monkeypatch.setattr("nanobot.trading.evidence.nodes.run_market_data_agent", _market)
    install_evidence_stubs(monkeypatch, gate_allowed=False)
    monkeypatch.setattr("nanobot.trading.evidence.nodes.run_market_data_agent", _market)

    turn = TurnSession()
    first = await fetch_evidence_nodes(["market_data"], session=turn)
    pipeline = turn.pipeline
    second = await fetch_evidence_nodes(["structure"], session=turn)
    assert turn.pipeline is pipeline
    assert calls["market"] == 1
    assert first["nodes"]["market_data"] is not None
    assert second["nodes"]["structure"] is not None
    assert "market_data" in second["present_nodes"]
    assert "structure" in second["present_nodes"]
    assert first["display"].get("mid") == "2400.00"


@pytest.mark.asyncio
async def test_get_gold_quote_alias_uses_market_data_when_on(monkeypatch) -> None:
    monkeypatch.setenv("LONORA_UNIFIED_LOOP", "on")
    payload = {
        "aborted": False,
        "nodes": {
            "market_data": {
                "quote_bid": 2399.5,
                "quote_ask": 2400.5,
                "quote_mid": 2400.0,
                "tradeable": True,
            }
        },
        "display": {"bid": "2399.50", "ask": "2400.50", "mid": "2400.00"},
    }
    monkeypatch.setattr(
        "nanobot.trading.unified_evidence.fetch_evidence_nodes",
        AsyncMock(return_value=payload),
    )
    tool = GetGoldQuoteTool(bus=None)
    raw = await tool.execute()
    body = json.loads(raw)
    assert body["display"]["mid"] == "2400.00"
    assert body["symbol"] == "XAUUSD"


def test_plan_turn_still_attaches_cards_when_flag_off(monkeypatch) -> None:
    monkeypatch.delenv("LONORA_UNIFIED_LOOP", raising=False)
    from nanobot.trading.turn_planner import plan_turn

    plan = plan_turn("كم سعر الذهب؟")
    assert plan.mode == "market_data_only"
    assert "market_data" in plan.nodes
