"""Deliver outcome transition alerts to Telegram/WhatsApp."""

from __future__ import annotations

from typing import Any

from nanobot.bus.events import OutboundMessage
from nanobot.trading.gold import DATA_SYMBOL
from nanobot.trading.oanda import fetch_quote
from nanobot.trading.recommendations.followup import refresh_recommendation_outcomes
from nanobot.trading.recommendations.outcome_alerts import (
    format_outcome_alert,
    should_alert_transition,
    transition_to_web_payload,
)


async def collect_outcome_alerts() -> list[OutboundMessage]:
    """Refresh stored recommendations and build user-visible alerts for transitions."""
    live_price: float | None = None
    try:
        quote = fetch_quote(DATA_SYMBOL)
        live_price = quote.mid if quote else None
    except Exception:
        live_price = None

    _, transitions = refresh_recommendation_outcomes(live_price=live_price)
    messages: list[OutboundMessage] = []
    for transition in transitions:
        if not should_alert_transition(transition):
            continue
        messages.append(
            _outcome_message(
                transition.row,
                transition.current,
                live_price=live_price,
            )
        )
    return messages


def outcome_web_alerts_from_transitions(
    transitions: list,
    *,
    live_price: float | None = None,
) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    for transition in transitions:
        if not should_alert_transition(transition):
            continue
        alerts.append(transition_to_web_payload(transition, live_price=live_price))
    return alerts


def collect_outcome_web_alerts() -> list[dict[str, Any]]:
    """Refresh recommendations and return WebUI-friendly outcome payloads."""
    live_price: float | None = None
    try:
        quote = fetch_quote(DATA_SYMBOL)
        live_price = quote.mid if quote else None
    except Exception:
        live_price = None

    _, transitions = refresh_recommendation_outcomes(live_price=live_price)
    return outcome_web_alerts_from_transitions(transitions, live_price=live_price)


def _outcome_message(
    row: dict[str, Any],
    status: str,
    *,
    live_price: float | None,
) -> OutboundMessage:
    telegram = format_outcome_alert(row, status, live_price=live_price, html_mode=True)
    whatsapp = format_outcome_alert(row, status, live_price=live_price, html_mode=False)
    return OutboundMessage(
        channel="",
        chat_id="",
        content=telegram,
        metadata={
            "trading_outcome_alert": True,
            "whatsapp_content": whatsapp,
            "parse_mode": "HTML",
        },
    )
