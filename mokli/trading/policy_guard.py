"""Policy Guard — Hard Law interceptors (G1–G20) for agent tool calls.

Enforcement is tool scope plus the interceptors below; the LLM chooses tools,
the guard only blocks or normalizes what would violate Hard Law.
"""

from __future__ import annotations

from dataclasses import dataclass


class PolicyViolation(Exception):  # noqa: N818 — public Hard Law API name
    """A tool call cannot be executed under Hard Law."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


KERNEL_TOOL_NAMES = frozenset({"run_trading_kernel", "analyze_gold"})
SPAWN_TOOL_NAMES = frozenset({"spawn"})
MT5_EXECUTION_TOOLS = frozenset(
    {
        "mt5_propose_order",
        "mt5_confirm_order",
        "mt5_modify_order",
        "mt5_cancel_order",
        "mt5_close_position",
    }
)
EVIDENCE_TOOL_NAMES = frozenset({"fetch_evidence", "get_gold_quote"})
SUBAGENT_FORBIDDEN_TOOLS = (
    KERNEL_TOOL_NAMES
    | SPAWN_TOOL_NAMES
    | MT5_EXECUTION_TOOLS
    | frozenset(
        {
            "manage_trading_plan",
            "run_trading_team",
            "get_gate_report",
            "mt5_get_account",
        }
    )
)

# Structural split: analysis tools are never the HITL execution surface.
assert KERNEL_TOOL_NAMES.isdisjoint(MT5_EXECUTION_TOOLS)
assert EVIDENCE_TOOL_NAMES.isdisjoint(MT5_EXECUTION_TOOLS)


@dataclass(frozen=True)
class ToolCallPermit:
    tool_name: str
    args: dict
    adjustments: tuple[str, ...] = ()


def validate_turn_input(
    message: str,
    *,
    session_key: str | None,
    interval: str = "15m",
    is_subagent: bool = False,
    turn_id: str | None = None,
):
    """Bind gold-only turn state. Called only when unified loop is not off."""
    from mokli.trading.gold import DATA_SYMBOL, require_gold
    from mokli.trading.turn_session import TurnSession

    require_gold(DATA_SYMBOL)
    return TurnSession(
        turn_id=turn_id,
        session_key=session_key,
        interval=interval,
        is_subagent=is_subagent,
    )


def validate_tool_call(
    tool_name: str,
    args: dict,
    *,
    is_subagent: bool | None = None,
) -> ToolCallPermit:
    """Hard Law interceptor for unified-loop tool calls."""
    from mokli.trading.evidence.node_sets import SYNTHESIS_REQUIRED_NODES
    from mokli.trading.evidence.nodes import NODE_REGISTRY
    from mokli.trading.gold import DATA_SYMBOL, require_gold
    from mokli.trading.turn_session import current_turn_session

    turn = current_turn_session()
    subagent = is_subagent if is_subagent is not None else bool(turn and turn.is_subagent)
    adjustments: list[str] = []
    params = dict(args or {})

    if subagent and tool_name in SUBAGENT_FORBIDDEN_TOOLS:
        raise PolicyViolation(f"Subagents cannot call {tool_name}")

    if tool_name in EVIDENCE_TOOL_NAMES or tool_name == "fetch_evidence":
        symbol = params.get("symbol") or DATA_SYMBOL
        try:
            require_gold(symbol)
        except Exception as exc:
            from mokli.trading.gold import GoldOnlyError

            if isinstance(exc, GoldOnlyError):
                raise PolicyViolation(str(exc)) from exc
            raise
        params["symbol"] = DATA_SYMBOL
        nodes = params.get("nodes")
        if nodes:
            unknown = sorted(set(nodes) - set(NODE_REGISTRY))
            if unknown:
                raise PolicyViolation(f"Unknown evidence nodes: {', '.join(unknown)}")

    if tool_name in KERNEL_TOOL_NAMES:
        gather = params.get("gather_missing")
        if gather is None:
            gather = True
        if turn is not None and not gather:
            missing = sorted(SYNTHESIS_REQUIRED_NODES - turn.present_nodes())
            if missing:
                raise PolicyViolation("Missing synthesis evidence nodes: " + ", ".join(missing))

    if turn is not None:
        turn.record_tool(tool_name)
        turn.adjustments.extend(adjustments)

    return ToolCallPermit(tool_name=tool_name, args=params, adjustments=tuple(adjustments))
