"""Shared trading outbound helpers (locale + artifact metadata).

Tools decide whether to publish UI cards via ``should_publish_trading_ui``.
"""

from __future__ import annotations

from typing import Any

from nanobot.bus.events import OUTBOUND_META_AGENT_UI, OutboundMessage
from nanobot.trading.locale import locale_from_text, normalize_locale


def operator_locale(text: str | None = None, locale: str | None = None) -> str:
    if locale:
        return normalize_locale(locale)
    return normalize_locale(locale_from_text(text or ""))


def trading_artifacts_data(artifacts: list[dict[str, Any]] | None, locale: str) -> dict[str, Any]:
    return {"artifacts": list(artifacts or []), "locale": operator_locale(locale=locale)}


def agent_ui_metadata(kind: str, data: dict[str, Any]) -> dict[str, Any]:
    return {OUTBOUND_META_AGENT_UI: {"kind": kind, "data": data}}


def outbound_trading_artifacts_metadata(
    artifacts: list[dict[str, Any]] | None,
    locale: str,
) -> dict[str, Any]:
    if not artifacts:
        return {}
    return agent_ui_metadata("trading_artifacts", trading_artifacts_data(artifacts, locale))


def outbound_trading_artifacts_message(
    *,
    channel: str,
    chat_id: str,
    content: str,
    artifacts: list[dict[str, Any]] | None,
    locale: str,
    buttons: list[list[str]] | None = None,
) -> OutboundMessage:
    return OutboundMessage(
        channel=channel,
        chat_id=chat_id,
        content=content,
        buttons=buttons or [],
        metadata=outbound_trading_artifacts_metadata(artifacts, locale),
    )


def outbound_trading_result_message(
    wire: dict[str, Any],
    *,
    channel: str,
    chat_id: str,
) -> OutboundMessage:
    decision = str(wire.get("decision", "wait")).upper()
    summary = str(wire.get("summary", "")).strip()
    return OutboundMessage(
        channel=channel,
        chat_id=chat_id,
        content=summary or decision,
        metadata=agent_ui_metadata("trading_result", wire),
    )
