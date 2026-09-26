"""Shadow serving-path identity: extra logs, no extra store, no mutate when off/shadow."""

from __future__ import annotations

from nanobot.bus.events import OutboundMessage
from nanobot.trading.delivery import finalize_turn_outbound


def test_finalize_is_identity_when_flag_off(monkeypatch) -> None:
    monkeypatch.delenv("LONORA_UNIFIED_LOOP", raising=False)
    outbound = OutboundMessage(channel="cli", chat_id="x", content="BUY XAUUSD now 2500")
    result = finalize_turn_outbound(outbound, user_text="buy gold")
    assert result is outbound
    assert result.content == "BUY XAUUSD now 2500"


def test_shadow_finalize_does_not_mutate_outbound(monkeypatch) -> None:
    monkeypatch.setenv("LONORA_UNIFIED_LOOP", "shadow")
    monkeypatch.delenv("LONORA_AGENT_FIRST", raising=False)
    outbound = OutboundMessage(channel="cli", chat_id="x", content="BUY XAUUSD now 2500")
    result = finalize_turn_outbound(outbound, user_text="كم سعر الذهب؟")
    assert result is outbound
    assert result.content == "BUY XAUUSD now 2500"


def test_on_finalize_strips_unauthorized_buy(monkeypatch) -> None:
    monkeypatch.setenv("LONORA_UNIFIED_LOOP", "on")
    monkeypatch.delenv("LONORA_AGENT_FIRST", raising=False)
    outbound = OutboundMessage(channel="cli", chat_id="x", content="BUY XAUUSD now 2500")
    result = finalize_turn_outbound(outbound, user_text="buy now")
    assert result is not None
    assert result.content != outbound.content
    assert "BUY" not in result.content.upper()
