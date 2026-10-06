"""Agent-controlled trading UI delivery (no automatic side-effects)."""

from __future__ import annotations


def should_publish_trading_ui(present_ui: bool) -> bool:
    """Trading tools push Mokli/Telegram cards only when the LLM opts in."""
    return bool(present_ui)
