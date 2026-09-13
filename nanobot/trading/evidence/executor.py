"""Execute an EvidenceGraph against a PipelineContext."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from nanobot.trading.evidence.context import PipelineContext
from nanobot.trading.evidence.graph import DEFAULT_ANALYSIS_GRAPH, EvidenceGraph
from nanobot.trading.evidence.nodes import NODE_REGISTRY, get_node
from nanobot.trading.stage_events import StageEvent, emit_stage

StageTracker = Callable[[StageEvent], None]


def _noop_track(_: StageEvent) -> None:
    return None


async def _run_node(
    node_id: str,
    ctx: PipelineContext,
    track: StageTracker,
) -> str | None:
    """Run one node; return abort reason when the pipeline should stop."""
    node = get_node(node_id)
    stage = node.stage
    if stage is not None:
        track(emit_stage(stage, "running"))
    try:
        await node.execute(ctx)
    except Exception:
        if stage is not None:
            track(emit_stage(stage, "failed"))
        raise
    if stage is not None:
        status = "failed" if node_id == "market_data" and ctx.market_sync_failed else "done"
        track(emit_stage(stage, status))
    if ctx.aborted:
        return ctx.abort_reason or "pipeline aborted"
    return None


async def run_evidence_graph(
    ctx: PipelineContext,
    graph: EvidenceGraph = DEFAULT_ANALYSIS_GRAPH,
    *,
    track: StageTracker | None = None,
) -> PipelineContext:
    """Run all layers in ``graph``; stop early when a node sets ``ctx.aborted``."""
    track_fn = track or _noop_track
    unknown = graph.node_ids() - frozenset(NODE_REGISTRY)
    if unknown:
        raise ValueError(f"Graph references unknown nodes: {sorted(unknown)}")

    for layer in graph.layers:
        if len(layer) == 1:
            abort = await _run_node(layer[0], ctx, track_fn)
            if abort is not None:
                return ctx
            continue

        results = await asyncio.gather(
            *(_run_node(node_id, ctx, track_fn) for node_id in layer),
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, Exception):
                raise result
        if ctx.aborted:
            return ctx

    return ctx


def stage_sequence_from_graph(
    graph: EvidenceGraph = DEFAULT_ANALYSIS_GRAPH,
) -> list[tuple[str, str]]:
    """Return (stage, status) pairs emitted on a successful full run (for tests)."""
    sequence: list[tuple[str, str]] = []
    for layer in graph.layers:
        for node_id in layer:
            stage = NODE_REGISTRY[node_id].stage
            if stage is None:
                continue
            sequence.append((stage, "running"))
            sequence.append((stage, "done"))
    return sequence
