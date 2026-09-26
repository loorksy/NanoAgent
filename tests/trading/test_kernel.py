"""Group A remaining kernel Hard Law tests + Group B loop behaviour."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from evidence_stubs import fake_market, install_evidence_stubs

from mokli.agent.tools.trading_chart import GetGoldQuoteTool
from mokli.trading.kernel import run_trading_kernel
from mokli.trading.policy_guard import PolicyViolation
from mokli.trading.recommendations.store import latest_live_recommendation, store_recommendation
from mokli.trading.turn_session import TurnSession, turn_session_scope
from mokli.trading.types import (
    AgentMarketContext,
    AgentRecommendation,
    FinalDecisionResult,
    GateChainResult,
    GateVerdict,
    MarketSync,
)
from mokli.trading.unified_evidence import fetch_evidence_nodes


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
    monkeypatch.setattr("mokli.config.paths.get_data_dir", lambda: tmp_path)
    monkeypatch.setattr("mokli.trading.recommendations.store.get_data_dir", lambda: tmp_path)
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

    monkeypatch.setattr("mokli.trading.kernel.refuse_repeat_error", lambda **_k: None)
    monkeypatch.setattr("mokli.trading.kernel.run_final_decision_synthesizer", _synth)
    monkeypatch.setattr("mokli.trading.kernel.run_gate_chain", _chain)
    monkeypatch.setattr(
        "mokli.trading.gates.reprice_loop.apply_g7_reprice_loop",
        _reprice,
    )
    monkeypatch.setattr("mokli.trading.kernel.fetch_quote", lambda *_a, **_k: None)

    with turn_session_scope(TurnSession()):
        result = await run_trading_kernel(gather_missing=True, store=False, present_ui=False)
    assert result.decision.decision == "wait"
    assert result.decision.recommendation.action == "wait"
    assert result.decision.decision != "sell"
    assert result.recommendation_id in {None, ""}


@pytest.mark.asyncio
async def test_pipeline_context_shared_across_fetch_evidence_calls(monkeypatch) -> None:
    market = fake_market()
    calls = {"market": 0}

    def _market(_symbol, _interval):
        calls["market"] += 1
        return market

    monkeypatch.setattr("mokli.trading.evidence.nodes.run_market_data_agent", _market)
    install_evidence_stubs(monkeypatch, gate_allowed=False)
    monkeypatch.setattr("mokli.trading.evidence.nodes.run_market_data_agent", _market)

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
async def test_get_gold_quote_uses_market_data_node(monkeypatch) -> None:
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
        "mokli.agent.tools.trading_chart.fetch_evidence_nodes",
        AsyncMock(return_value=payload),
    )
    monkeypatch.setattr(
        "mokli.agent.tools.trading_chart.load_trading_config",
        lambda: MagicMock(oanda_configured=True),
    )
    tool = GetGoldQuoteTool(bus=None)
    raw = await tool.execute()
    body = json.loads(raw)
    assert body["display"]["mid"] == "2400.00"
    assert body["symbol"] == "XAUUSD"
