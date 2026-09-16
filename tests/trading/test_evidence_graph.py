"""Tests for Phase H evidence graph runtime."""

import pytest

from nanobot.trading.evidence import (
    DEFAULT_ANALYSIS_GRAPH,
    NODE_REGISTRY,
    PipelineContext,
    get_node,
    run_evidence_graph,
    stage_sequence_from_graph,
)
from nanobot.trading.evidence.graph import DEFAULT_ANALYSIS_LAYERS


def test_default_graph_matches_legacy_layer_order():
    assert DEFAULT_ANALYSIS_LAYERS == (
        ("market_data",),
        ("structure", "liquidity", "supply_demand", "multi_timeframe"),
        ("news",),
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
    from tests.trading.evidence_stubs import install_evidence_stubs

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
    from nanobot.trading.types import AgentMarketContext, MarketSync

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
        "nanobot.trading.evidence.nodes.run_market_data_agent",
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
    from nanobot.trading.orchestrator import run_unified_chart_agent
    from tests.trading.evidence_stubs import install_evidence_stubs

    install_evidence_stubs(monkeypatch)
    result = await run_unified_chart_agent(store=False)
    assert result.decision is not None
    stage_names = [s["stage"] for s in result.stages]
    assert "market_data" in stage_names
    assert "structure" in stage_names
    assert "research" in stage_names


@pytest.mark.asyncio
async def test_orchestrator_blocks_repeat_lesson(monkeypatch):
    from nanobot.trading.intel.postmortem import LossRecord
    from nanobot.trading.orchestrator import run_unified_chart_agent
    from nanobot.trading.types import AgentRecommendation, FinalDecisionResult
    from tests.trading.evidence_stubs import install_evidence_stubs

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

    monkeypatch.setattr("nanobot.trading.orchestrator.run_final_decision_synthesizer", _buy)
    monkeypatch.setattr(
        "nanobot.trading.orchestrator.refuse_repeat_error",
        lambda **_k: LossRecord(2400, 2385, 1, "unknown", "structure", 10.0, "early_entry", "buy"),
    )
    result = await run_unified_chart_agent(store=False)
    assert result.decision.decision == "wait"
    assert "losing" in (result.decision.summary or "").lower()
