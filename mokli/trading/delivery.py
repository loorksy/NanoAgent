"""Shared trading outbound helpers (locale + artifact metadata).

Tools decide whether to publish UI cards via ``should_publish_trading_ui``.
"""

from __future__ import annotations

from typing import Any

from mokli.bus.events import OUTBOUND_META_AGENT_UI, OutboundMessage
from mokli.trading.locale import locale_from_text, normalize_locale


def silence_blocks(*, regime: str, material_change: bool) -> bool:
    """T-9.3 — no proactive ping in a range unless something material changed."""
    return regime == "range" and not material_change


def broadcast_channels(
    channels: list[str],
    *,
    regime: str = "trend",
    material_change: bool = True,
) -> list[str]:
    """T-6.7 — channels that should receive a proactive event after the silence gate."""
    if silence_blocks(regime=regime, material_change=material_change):
        return []
    seen: list[str] = []
    for name in channels:
        if name and name not in seen:
            seen.append(name)
    return seen


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
