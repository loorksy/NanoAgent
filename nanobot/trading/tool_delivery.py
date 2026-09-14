"""Agent-controlled trading UI delivery (no automatic side-effects)."""

from __future__ import annotations

from nanobot.trading.config import load_trading_config


def should_publish_trading_ui(present_ui: bool) -> bool:
    """Return whether trading tools may push WebUI/Telegram cards for this call.

    In agent-first mode the LLM must opt in with ``present_ui=true``. Legacy
    fast-path deployments keep automatic publishing when ``LONORA_AGENT_FIRST=false``.
    """
    config = load_trading_config()
    if config.agent_first_mode:
        return bool(present_ui)
    return True
