"""Run Evidence Nodes into the turn-scoped PipelineContext.

Does not import or call MT5 execution. Node implementations stay in evidence/.
"""

from __future__ import annotations

from typing import Any

from nanobot.trading.evidence.context import PipelineContext
from nanobot.trading.evidence.executor import run_evidence_graph
from nanobot.trading.evidence.graph import graph_for_nodes
from nanobot.trading.evidence.nodes import NODE_REGISTRY, get_node
from nanobot.trading.gold import DATA_SYMBOL, require_gold
from nanobot.trading.turn_session import TurnSession, current_turn_session, require_turn_session

_SERIALIZE_SKIP = frozenset({"candles"})


def expand_node_dependencies(node_ids: frozenset[str]) -> tuple[frozenset[str], tuple[str, ...]]:
    """Include declared depends_on so nodes can execute without crashing."""
    expanded = set(node_ids)
    added: list[str] = []
    changed = True
    while changed:
        changed = False
        for node_id in list(expanded):
            node = get_node(node_id)
            for dep in node.depends_on:
                if dep not in expanded:
                    expanded.add(dep)
                    added.append(dep)
                    changed = True
    return frozenset(expanded), tuple(added)


def _json_safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 4:
        return None
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _json_safe(v, depth=depth + 1) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item, depth=depth + 1) for item in value[:40]]
    if hasattr(value, "__dataclass_fields__"):
        payload: dict[str, Any] = {}
        for name in value.__dataclass_fields__:
            if name in _SERIALIZE_SKIP:
                continue
            payload[name] = _json_safe(getattr(value, name), depth=depth + 1)
        return payload
    return str(value)


def serialize_node_slice(ctx: PipelineContext, node_id: str) -> Any:
    attr = {
        "market_data": "market",
        "structure": "structure",
        "liquidity": "liquidity",
        "supply_demand": "supply_demand",
        "multi_timeframe": "mtf",
        "news": "news",
        "geometry": "geometry",
        "risk": "risk",
        "visual_capture": "visual",
    }.get(node_id)
    if attr is None:
        return None
    return _json_safe(getattr(ctx, attr, None))


def record_market_prices(session: TurnSession, ctx: PipelineContext) -> None:
    market = ctx.market
    if market is None:
        return
    display: dict[str, str | None] = {}
    for key, raw in (("bid", market.quote_bid), ("ask", market.quote_ask), ("mid", market.quote_mid)):
        if raw is None:
            display[key] = None
            continue
        text = f"{float(raw):.2f}"
        display[key] = text
        session.add_price_strings(text)
    session.quote_display = display


async def fetch_evidence_nodes(
    node_ids: list[str] | tuple[str, ...],
    *,
    interval: str = "15m",
    refresh: bool = False,
    session: TurnSession | None = None,
    visual_capture: Any | None = None,
) -> dict[str, Any]:
    """Run a subgraph on the turn PipelineContext and return JSON slices."""
    turn = session or current_turn_session() or require_turn_session()
    requested = tuple(node_ids)
    unknown = sorted(set(requested) - set(NODE_REGISTRY))
    if unknown:
        from nanobot.trading.policy_guard import PolicyViolation

        raise PolicyViolation(f"Unknown evidence nodes: {', '.join(unknown)}", plan=None)

    require_gold(DATA_SYMBOL)
    pipeline = turn.ensure_pipeline(interval=interval)
    if visual_capture is not None:
        pipeline.visual_capture = visual_capture

    wanted = set(requested)
    if not refresh:
        wanted -= set(turn.present_nodes())
    expanded, injected = expand_node_dependencies(frozenset(wanted) if wanted else frozenset(requested))
    if not refresh:
        expanded = frozenset(nid for nid in expanded if nid not in turn.present_nodes() or nid in wanted)
    if injected:
        turn.adjustments.append(f"injected_depends_on:{','.join(injected)}")

    if expanded:
        graph = graph_for_nodes(expanded)
        pipeline = await run_evidence_graph(pipeline, graph)
        turn.pipeline = pipeline
        for node_id in sorted(expanded):
            if node_id not in turn.nodes_fetched:
                turn.nodes_fetched.append(node_id)

    record_market_prices(turn, pipeline)
    slices = {node_id: serialize_node_slice(pipeline, node_id) for node_id in requested}
    return {
        "symbol": DATA_SYMBOL,
        "interval": pipeline.interval,
        "aborted": pipeline.aborted,
        "abort_reason": pipeline.abort_reason or None,
        "nodes": slices,
        "present_nodes": sorted(turn.present_nodes()),
        "display": dict(turn.quote_display),
        "instruction": (
            "Copy display.mid (or bid/ask) verbatim — never invent prices. "
            "This JSON is evidence only and is not a BUY/SELL recommendation."
        ),
    }
