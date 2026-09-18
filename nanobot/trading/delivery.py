"""Shared trading outbound helpers (locale + artifact metadata).

Legacy fast-path callers keep unconditional publish. Agent-first tools still
gate with should_publish_trading_ui.
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


def finalize_turn_outbound(
    outbound: OutboundMessage | None,
    *,
    user_text: str = "",
    mutate: bool | None = None,
) -> OutboundMessage | None:
    """Apply output policy and shadow logs. No-op when unified loop is off."""
    from nanobot.trading.config import peek_unified_loop_env, unified_loop_mode

    peeked = peek_unified_loop_env()
    if peeked is None:
        return outbound
    mode = unified_loop_mode()
    if mode == "off":
        return outbound

    from nanobot.trading.shadow import log_regex_counterfactual, maybe_mark_dual_run_sample

    try:
        log_regex_counterfactual(user_text)
        maybe_mark_dual_run_sample()
    except Exception:
        from loguru import logger

        logger.exception("unified loop shadow log failed")

    if mode != "on" or outbound is None:
        return outbound

    from nanobot.trading.policy_guard import validate_turn_output

    should_mutate = True if mutate is None else mutate
    content = validate_turn_output(outbound.content or "", mutate=should_mutate)
    if content == outbound.content:
        return outbound
    return OutboundMessage(
        channel=outbound.channel,
        chat_id=outbound.chat_id,
        content=content,
        reply_to=outbound.reply_to,
        media=list(outbound.media or []),
        metadata=dict(outbound.metadata or {}),
        buttons=list(outbound.buttons or []),
        event=outbound.event,
    )
