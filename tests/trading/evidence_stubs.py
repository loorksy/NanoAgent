"""Shared stubs for evidence-graph integration tests."""

from __future__ import annotations

from typing import Any

from nanobot.trading.types import (
    AgentMarketContext,
    Candle,
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


def fake_market() -> AgentMarketContext:
    return AgentMarketContext(
        symbol="XAUUSD",
        interval="15m",
        candles=[Candle(i, 2395, 2410, 2390, 2400, 1) for i in range(20)],
        last_close=2400.0,
        atr=8.0,
        sync=MarketSync(ok=True),
        quote_mid=2400.0,
    )


def install_evidence_stubs(monkeypatch: Any, *, gate_allowed: bool = True) -> dict[str, Any]:
    """Patch evidence node agents (and optional gate chain) for orchestrator tests."""
    market = fake_market()
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
    visual = VisualReview(state="not_checked", requested=["15m"], captured=[], missing=["15m"])

    monkeypatch.setattr(
        "nanobot.trading.evidence.nodes.run_market_data_agent",
        lambda *_a, **_k: market,
    )
    monkeypatch.setattr(
        "nanobot.trading.evidence.nodes.run_structure_agent",
        lambda *_a, **_k: structure,
    )
    monkeypatch.setattr(
        "nanobot.trading.evidence.nodes.run_liquidity_agent",
        lambda *_a, **_k: liquidity,
    )
    monkeypatch.setattr(
        "nanobot.trading.evidence.nodes.run_supply_demand_agent",
        lambda *_a, **_k: supply,
    )
    monkeypatch.setattr(
        "nanobot.trading.evidence.nodes.run_multi_timeframe_agent",
        lambda *_a, **_k: mtf,
    )
    monkeypatch.setattr(
        "nanobot.trading.evidence.nodes.run_news_macro_agent",
        lambda *_a, **_k: news,
    )
    monkeypatch.setattr(
        "nanobot.trading.evidence.nodes.run_risk_agent",
        lambda *_a, **_k: risk,
    )

    async def _visual(_lead: str, *, capture=None):
        return visual, []

    monkeypatch.setattr("nanobot.trading.evidence.nodes.capture_visual_evidence", _visual)

    if gate_allowed:
        allowed = GateChainResult(verdicts=[], allowed=True, confidence_delta=0)

        async def _allowed(*_a, **_k):
            return allowed

        monkeypatch.setattr("nanobot.trading.orchestrator.run_gate_chain", _allowed)

        async def _no_reprice(chain, gates, plan, rec):
            return chain, plan, rec

        monkeypatch.setattr(
            "nanobot.trading.gates.reprice_loop.apply_g7_reprice_loop",
            _no_reprice,
        )

    return {
        "market": market,
        "structure": structure,
        "liquidity": liquidity,
        "supply": supply,
        "mtf": mtf,
        "news": news,
        "risk": risk,
        "visual": visual,
    }
