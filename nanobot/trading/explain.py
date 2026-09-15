"""Explain the last trading kernel result — no generic LLM improvisation."""

from __future__ import annotations

from typing import Any

from nanobot.trading.i18n import tr


def last_trading_wire_from_messages(messages: list[dict[str, Any]]) -> dict[str, Any] | None:
    for msg in reversed(messages):
        if msg.get("role") != "assistant":
            continue
        wire = msg.get("_trading_wire")
        if isinstance(wire, dict):
            return wire
    return None


def build_trading_explain(wire: dict[str, Any], *, locale: str) -> str:
    decision = str(wire.get("decision") or "wait").upper()
    summary = str(wire.get("summary") or "").strip()
    refusal = wire.get("refusalSummary") or wire.get("refusal_summary")
    reasons = list(wire.get("keyReasons") or wire.get("key_reasons") or [])
    warnings = list(wire.get("riskWarnings") or wire.get("risk_warnings") or [])

    lines = [tr("explain.header", locale, decision=decision)]
    if summary:
        lines.append(summary)
    if refusal:
        lines.append(tr("explain.reason", locale, reason=str(refusal)))
    for item in reasons[:5]:
        text = str(item).strip()
        if text:
            lines.append(f"• {text}")
    for item in warnings[:3]:
        text = str(item).strip()
        if text:
            lines.append(f"• {text}")
    lines.append(tr("explain.footer", locale))
    return "\n".join(lines)
