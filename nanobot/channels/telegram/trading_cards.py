"""Telegram HTML renderer for gold trading recommendation cards."""

from __future__ import annotations

from typing import Any

from nanobot.trading.cards.format import render_telegram_card


def render_recommendation_card(payload: dict[str, Any], *, locale: str | None = None) -> str:
    return render_telegram_card(payload, locale=locale)
