"""Execute an EvidenceGraph against a PipelineContext."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from mokli.trading.evidence.context import PipelineContext
from mokli.trading.evidence.graph import DEFAULT_ANALYSIS_GRAPH, EvidenceGraph
from mokli.trading.evidence.nodes import NODE_REGISTRY, get_node
from mokli.trading.observability import track_node_timing
from mokli.trading.stage_events import StageEvent, emit_stage

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
        with track_node_timing(node_id):
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


def _graph_order(graph: EvidenceGraph) -> list[str]:
    ordered: list[str] = []
    for layer in graph.layers:
        ordered.extend(layer)
    return ordered


def _ready_nodes(
    ordered: list[str],
    present: set[str],
    remaining: set[str],
    running: set[str],
) -> list[str]:
    """Nodes whose in-graph dependencies have already finished."""
    ready: list[str] = []
    for node_id in ordered:
        if node_id not in remaining:
            continue
        deps = [dep for dep in get_node(node_id).depends_on if dep in present]
        if any(dep in remaining or dep in running for dep in deps):
            continue
        ready.append(node_id)
    return ready


async def run_evidence_graph(
    ctx: PipelineContext,
    graph: EvidenceGraph = DEFAULT_ANALYSIS_GRAPH,
    *,
    track: StageTracker | None = None,
) -> PipelineContext:
    """Run ``graph`` by dependency. Stop scheduling when a node aborts or raises."""
    track_fn = track or _noop_track
    ordered = _graph_order(graph)
    present = set(ordered)
    unknown = present - frozenset(NODE_REGISTRY)
    if unknown:
        raise ValueError(f"Graph references unknown nodes: {sorted(unknown)}")

    remaining = set(ordered)
    running: dict[str, asyncio.Task[str | None]] = {}
    failure: Exception | None = None

    while remaining or running:
        if failure is None and not ctx.aborted:
            for node_id in _ready_nodes(ordered, present, remaining, set(running)):
                remaining.remove(node_id)
                running[node_id] = asyncio.create_task(_run_node(node_id, ctx, track_fn))
        elif running:
            # A failed candle download does not need the calendar that started with it.
            for task in running.values():
                task.cancel()
        if not running:
            break
        finished, _pending = await asyncio.wait(
            set(running.values()),
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in finished:
            node_id = next(key for key, value in running.items() if value is task)
            running.pop(node_id)
            try:
                task.result()
            except asyncio.CancelledError:
                continue
            except Exception as exc:
                if failure is None:
                    failure = exc
    if failure is not None:
        raise failure
    return ctx


def stage_sequence_from_graph(
    graph: EvidenceGraph = DEFAULT_ANALYSIS_GRAPH,
) -> list[tuple[str, str]]:
    """Return the declared layer order of stage events, not the concurrent runtime order."""
    sequence: list[tuple[str, str]] = []
    for layer in graph.layers:
        for node_id in layer:
            stage = NODE_REGISTRY[node_id].stage
            if stage is None:
                continue
            sequence.append((stage, "running"))
            sequence.append((stage, "done"))
    return sequence
