"""WhatsApp plain-text renderer for gold trading recommendation cards."""

from __future__ import annotations

from typing import Any

from nanobot.trading.cards.format import render_whatsapp_card


def render_recommendation_card(payload: dict[str, Any]) -> str:
    return render_whatsapp_card(payload)
