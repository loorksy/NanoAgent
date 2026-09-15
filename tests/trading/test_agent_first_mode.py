"""Agent-first routing: LLM + tools, no fast-path hijack."""

from nanobot.trading.config import load_trading_config


def test_agent_first_mode_defaults_true(monkeypatch) -> None:
    monkeypatch.delenv("LONORA_AGENT_FIRST", raising=False)
    assert load_trading_config().agent_first_mode is True


def test_agent_first_mode_can_disable_legacy_fast_path(monkeypatch) -> None:
    monkeypatch.setenv("LONORA_AGENT_FIRST", "false")
    assert load_trading_config().agent_first_mode is False
