"""Group A — Hard Law interceptors for the unified loop (flag-on only)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from nanobot.agent.tools.context import ToolContext
from nanobot.agent.tools.loader import ToolLoader
from nanobot.agent.tools.registry import ToolRegistry
from nanobot.config.schema import ToolsConfig
from nanobot.trading.output_policy import apply_output_policy
from nanobot.trading.policy_guard import PolicyViolation, validate_tool_call
from nanobot.trading.turn_session import TurnSession, turn_session_scope

_REPO = Path(__file__).resolve().parents[2]
_ANALYSIS_MODULES = [
    _REPO / "nanobot/trading/kernel.py",
    _REPO / "nanobot/trading/unified_evidence.py",
    _REPO / "nanobot/agent/tools/trading_evidence.py",
    _REPO / "nanobot/agent/tools/trading_kernel.py",
]
_MT5_MARKERS = (
    "nanobot.trading.mt5_execution",
    "nanobot.trading.mt5_metaapi",
    "nanobot.trading.mt5_proposals",
    "mt5_propose_order",
    "mt5_confirm_order",
    "mt5_modify_order",
    "mt5_cancel_order",
    "mt5_close_position",
)


def test_analysis_modules_cannot_import_mt5_execution() -> None:
    for path in _ANALYSIS_MODULES:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not any(marker in alias.name for marker in _MT5_MARKERS), path
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert not any(marker in module for marker in _MT5_MARKERS), path
                for alias in node.names:
                    assert alias.name not in _MT5_MARKERS, path
        for marker in _MT5_MARKERS:
            assert marker not in source, f"{path} mentions {marker}"


def test_kernel_refuses_missing_synthesis_nodes() -> None:
    session = TurnSession()
    with turn_session_scope(session):
        with pytest.raises(PolicyViolation, match="Missing synthesis evidence nodes"):
            validate_tool_call("run_trading_kernel", {"gather_missing": False})


def test_kernel_gather_missing_default_does_not_refuse() -> None:
    session = TurnSession()
    with turn_session_scope(session):
        permit = validate_tool_call("run_trading_kernel", {})
    assert permit.tool_name == "run_trading_kernel"


def test_evidence_rejects_nongold_symbol() -> None:
    with turn_session_scope(TurnSession()):
        with pytest.raises(PolicyViolation):
            validate_tool_call("fetch_evidence", {"nodes": ["market_data"], "symbol": "EURUSD"})


def test_unknown_node_is_policy_violation() -> None:
    with turn_session_scope(TurnSession()):
        with pytest.raises(PolicyViolation, match="Unknown evidence nodes"):
            validate_tool_call("fetch_evidence", {"nodes": ["not_a_real_node"]})


def test_output_policy_strips_unauthorized_buy_and_still_replies() -> None:
    rewritten = apply_output_policy("BUY XAUUSD now 2500", mutate=True)
    assert rewritten
    assert "BUY" not in rewritten.upper()
    assert "2500" not in rewritten
    assert "no issued recommendation" in rewritten.lower() or "platform price" in rewritten


def test_output_policy_rejects_price_absent_from_evidence_json() -> None:
    session = TurnSession()
    session.add_price_strings("4342.60")
    with turn_session_scope(session):
        rewritten = apply_output_policy("Gold is 3301.00", mutate=True)
    assert "3301.00" not in rewritten
    assert "4342.60" not in rewritten or "3301.00" not in rewritten
    assert "platform price" in rewritten


def test_output_policy_keeps_verbatim_display_mid() -> None:
    session = TurnSession()
    session.add_price_strings("4342.60")
    with turn_session_scope(session):
        rewritten = apply_output_policy("XAUUSD mid 4342.60", mutate=True)
    assert "4342.60" in rewritten


def test_subagent_registry_excludes_kernel_spawn_mt5(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LONORA_UNIFIED_LOOP", "on")
    ctx = ToolContext(config=ToolsConfig(), workspace=str(tmp_path), timezone="UTC")
    core = ToolRegistry()
    sub = ToolRegistry()
    loader = ToolLoader()
    loader.load(ctx, core, scope="core")
    loader.load(ctx, sub, scope="subagent")
    forbidden = {
        "run_trading_kernel",
        "analyze_gold",
        "spawn",
        "mt5_confirm_order",
        "mt5_propose_order",
        "mt5_modify_order",
        "mt5_cancel_order",
        "mt5_close_position",
        "manage_trading_plan",
    }
    for name in forbidden:
        assert not sub.has(name), name
        if name in {"run_trading_kernel"}:
            assert core.has(name)
    assert core.has("fetch_evidence")
    assert sub.has("fetch_evidence")
    assert not sub.has("get_gate_report")


def test_nested_spawn_from_subagent_fails_closed() -> None:
    session = TurnSession(is_subagent=True)
    with turn_session_scope(session):
        with pytest.raises(PolicyViolation, match="cannot call spawn"):
            validate_tool_call("spawn", {"task": "nested"})
        with pytest.raises(PolicyViolation, match="cannot call run_trading_kernel"):
            validate_tool_call("run_trading_kernel", {"gather_missing": True})
        with pytest.raises(PolicyViolation, match="cannot call mt5_confirm_order"):
            validate_tool_call("mt5_confirm_order", {"proposal_id": "x", "confirm": True})
