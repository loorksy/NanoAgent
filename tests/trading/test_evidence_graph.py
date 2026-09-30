"""Tests for Phase H evidence graph runtime."""

import asyncio
import threading

import pytest

from mokli.trading.evidence import (
    DEFAULT_ANALYSIS_GRAPH,
    NODE_REGISTRY,
    PipelineContext,
    get_node,
    run_evidence_graph,
    stage_sequence_from_graph,
)
from mokli.trading.evidence.graph import DEFAULT_ANALYSIS_LAYERS


def test_default_graph_matches_legacy_layer_order():
    assert DEFAULT_ANALYSIS_LAYERS == (
        ("market_data",),
        ("structure", "liquidity", "supply_demand", "multi_timeframe", "news"),
        ("geometry",),
        ("risk",),
        ("visual_capture",),
    )
    assert DEFAULT_ANALYSIS_GRAPH.node_ids() == frozenset(NODE_REGISTRY)


def test_all_registered_nodes_have_unique_ids():
    ids = [node.id for node in NODE_REGISTRY.values()]
    assert len(ids) == len(set(ids))


def test_geometry_node_is_silent():
    assert get_node("geometry").stage is None


def test_visual_capture_maps_to_research_stage():
    assert get_node("visual_capture").stage == "research"


def test_stage_sequence_skips_silent_nodes():
    sequence = stage_sequence_from_graph()
    stages = [stage for stage, _ in sequence]
    assert "geometry" not in stages
    assert stages.count("research") == 2  # running + done


@pytest.mark.asyncio
async def test_run_evidence_graph_full_analysis(monkeypatch):
    from evidence_stubs import install_evidence_stubs

    install_evidence_stubs(monkeypatch, gate_allowed=False)
    ctx = PipelineContext(symbol="XAUUSD", interval="15m")
    events: list[tuple[str, str]] = []

    def track(event) -> None:
        events.append((event.stage, event.status))

    result = await run_evidence_graph(ctx, track=track)
    assert not result.aborted
    assert result.market is not None
    assert result.market.sync.ok
    assert result.structure is not None
    assert result.liquidity is not None
    assert result.supply_demand is not None
    assert result.mtf is not None
    assert result.news is not None
    assert result.geometry is not None
    assert result.risk is not None
    assert result.visual is not None
    assert events[0] == ("market_data", "running")
    assert ("market_data", "done") in events
    assert ("research", "running") in events
    assert ("research", "done") in events


@pytest.mark.asyncio
async def test_market_data_failure_aborts_graph(monkeypatch):
    from mokli.trading.types import AgentMarketContext, MarketSync

    def _fail_market(_symbol: str, _interval: str):
        return AgentMarketContext(
            symbol="XAUUSD",
            interval="15m",
            last_close=0.0,
            atr=0.0,
            sync=MarketSync(ok=False, reason="offline"),
            candles=[],
        )

    monkeypatch.setattr(
        "mokli.trading.evidence.nodes.run_market_data_agent",
        _fail_market,
    )

    ctx = PipelineContext(symbol="XAUUSD", interval="15m")
    events: list[tuple[str, str]] = []

    def track(event) -> None:
        events.append((event.stage, event.status))

    result = await run_evidence_graph(ctx, track=track)
    assert result.aborted
    assert result.market_sync_failed
    assert result.structure is None
    assert ("market_data", "failed") in events
    assert ("structure", "running") not in events


@pytest.mark.asyncio
async def test_orchestrator_uses_evidence_graph(monkeypatch):
    from evidence_stubs import install_evidence_stubs

    from mokli.trading.kernel import run_trading_kernel

    install_evidence_stubs(monkeypatch)
    result = await run_trading_kernel(store=False)
    assert result.decision is not None
    stage_names = [s["stage"] for s in result.stages]
    assert "market_data" in stage_names
    assert "structure" in stage_names
    assert "final_decision" in stage_names


@pytest.mark.asyncio
async def test_orchestrator_blocks_repeat_lesson(monkeypatch):
    from evidence_stubs import install_evidence_stubs

    from mokli.trading.intel.postmortem import LossRecord
    from mokli.trading.kernel import run_trading_kernel
    from mokli.trading.types import AgentRecommendation, FinalDecisionResult

    install_evidence_stubs(monkeypatch)

    async def _buy(*_a, **_k):
        rec = AgentRecommendation(
            action="buy",
            plan_type="immediate",
            entry=2400,
            stop_loss=2385,
            targets=[2420],
        )
        return FinalDecisionResult(
            decision="buy",
            confidence=0.7,
            summary="buy",
            key_reasons=[],
            risk_warnings=[],
            recommendation=rec,
        )

    monkeypatch.setattr("mokli.trading.kernel.run_final_decision_synthesizer", _buy)
    monkeypatch.setattr(
        "mokli.trading.kernel.refuse_repeat_error",
        lambda **_k: LossRecord(2400, 2385, 1, "unknown", "structure", 10.0, "early_entry", "buy"),
    )
    result = await run_trading_kernel(store=False)
    assert result.decision.decision == "wait"
    assert "losing" in (result.decision.summary or "").lower()


def _wait_until_both(name: str, started: list[str], release: threading.Event) -> None:
    started.append(name)
    if len(started) >= 2:
        release.set()
    if not release.wait(timeout=1):
        raise TimeoutError(name)


@pytest.mark.asyncio
async def test_screenshot_overlaps_risk(monkeypatch) -> None:
    """A chart capture needs market data only, so it does not wait for risk."""
    from evidence_stubs import install_evidence_stubs

    from mokli.trading.types import VisualReview

    install_evidence_stubs(monkeypatch)
    started: list[str] = []
    release = threading.Event()

    async def fake_capture(*_args, **_kwargs):
        await asyncio.to_thread(_wait_until_both, "visual", started, release)
        review = VisualReview(state="not_checked", requested=["15m"], captured=[], missing=["15m"])
        return review, []

    def fake_risk(*_args, **_kwargs):
        _wait_until_both("risk", started, release)
        from mokli.trading.types import RiskAgentResult, TradeCandidate, TradeValidationResult

        buy = TradeCandidate("cand-bull-1", "buy", 2400, "market", 2385, [2420], 2.0, 0.8)
        return RiskAgentResult(
            proposed_trade=buy,
            validation=TradeValidationResult(accepted=True, reasons=[]),
            selected_candidate=buy,
            candidates=[buy],
        )

    monkeypatch.setattr("mokli.trading.evidence.nodes.capture_visual_evidence", fake_capture)
    monkeypatch.setattr("mokli.trading.evidence.nodes.run_risk_agent", fake_risk)

    ctx = PipelineContext(symbol="XAUUSD", interval="15m")
    await asyncio.wait_for(run_evidence_graph(ctx), timeout=2)
    assert set(started) == {"visual", "risk"}
    assert ctx.visual is not None
    assert ctx.risk is not None


@pytest.mark.asyncio
async def test_risk_overlaps_a_slow_higher_timeframe_fetch(monkeypatch) -> None:
    """Risk depends on structure and supply, not on the higher-timeframe download."""
    from evidence_stubs import install_evidence_stubs

    install_evidence_stubs(monkeypatch)
    started: list[str] = []
    release = threading.Event()

    def fake_mtf(*_args, **_kwargs):
        _wait_until_both("mtf", started, release)
        from mokli.trading.types import MultiTimeframeResult

        return MultiTimeframeResult("bullish", "bullish", "bullish", False)

    def fake_risk(*_args, **_kwargs):
        _wait_until_both("risk", started, release)
        from mokli.trading.types import RiskAgentResult, TradeCandidate, TradeValidationResult

        buy = TradeCandidate("cand-bull-1", "buy", 2400, "market", 2385, [2420], 2.0, 0.8)
        return RiskAgentResult(
            proposed_trade=buy,
            validation=TradeValidationResult(accepted=True, reasons=[]),
            selected_candidate=buy,
            candidates=[buy],
        )

    monkeypatch.setattr("mokli.trading.evidence.nodes.run_multi_timeframe_agent", fake_mtf)
    monkeypatch.setattr("mokli.trading.evidence.nodes.run_risk_agent", fake_risk)

    ctx = PipelineContext(symbol="XAUUSD", interval="15m")
    await asyncio.wait_for(run_evidence_graph(ctx), timeout=2)
    assert set(started) == {"mtf", "risk"}
