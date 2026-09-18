"""Group C — LONORA_UNIFIED_LOOP flag isolation and invalid-combo fallback."""

from __future__ import annotations

from nanobot.trading.config import (
    load_trading_config,
    peek_unified_loop_env,
    unified_loop_active,
    unified_loop_mode,
    unified_loop_serving,
)


def test_unified_loop_defaults_off(monkeypatch) -> None:
    monkeypatch.delenv("LONORA_UNIFIED_LOOP", raising=False)
    monkeypatch.delenv("LONORA_AGENT_FIRST", raising=False)
    assert peek_unified_loop_env() is None
    assert unified_loop_mode() == "off"
    assert unified_loop_active() is False
    assert unified_loop_serving() is False
    assert load_trading_config().unified_loop_mode == "off"


def test_unified_loop_invalid_value_falls_back_off(monkeypatch) -> None:
    monkeypatch.setenv("LONORA_UNIFIED_LOOP", "maybe")
    assert unified_loop_mode() == "off"
    assert unified_loop_serving() is False


def test_unified_on_with_agent_first_false_falls_back_off(monkeypatch) -> None:
    monkeypatch.setenv("LONORA_UNIFIED_LOOP", "on")
    monkeypatch.setenv("LONORA_AGENT_FIRST", "false")
    assert unified_loop_mode() == "off"
    assert unified_loop_serving() is False
    assert load_trading_config().agent_first_mode is False


def test_unified_shadow_is_not_serving(monkeypatch) -> None:
    monkeypatch.setenv("LONORA_UNIFIED_LOOP", "shadow")
    monkeypatch.delenv("LONORA_AGENT_FIRST", raising=False)
    assert unified_loop_mode() == "shadow"
    assert unified_loop_active() is True
    assert unified_loop_serving() is False


def test_unified_tools_unregistered_when_off(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("LONORA_UNIFIED_LOOP", raising=False)
    from nanobot.agent.tools.context import ToolContext
    from nanobot.agent.tools.loader import ToolLoader
    from nanobot.agent.tools.registry import ToolRegistry
    from nanobot.config.schema import ToolsConfig

    ctx = ToolContext(config=ToolsConfig(), workspace=str(tmp_path), timezone="UTC")
    registry = ToolRegistry()
    ToolLoader().load(ctx, registry, scope="core")
    assert not registry.has("fetch_evidence")
    assert not registry.has("run_trading_kernel")
    assert not registry.has("get_gate_report")
    assert registry.has("analyze_gold")
    assert registry.has("get_gold_quote")


def test_unified_on_with_agent_first_default_serves(monkeypatch) -> None:
    monkeypatch.setenv("LONORA_UNIFIED_LOOP", "on")
    monkeypatch.delenv("LONORA_AGENT_FIRST", raising=False)
    assert unified_loop_mode() == "on"
    assert unified_loop_serving() is True


def test_shadow_sample_default_is_ten(monkeypatch) -> None:
    monkeypatch.delenv("LONORA_UNIFIED_LOOP_SHADOW_SAMPLE", raising=False)
    assert load_trading_config().unified_loop_shadow_sample == 10
