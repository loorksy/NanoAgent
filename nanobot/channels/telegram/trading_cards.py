"""Telegram HTML renderer for gold trading recommendation cards."""

from __future__ import annotations

from typing import Any


def render_recommendation_card(payload: dict[str, Any]) -> str:
    decision = str(payload.get("decision", "wait")).upper()
    summary = str(payload.get("summary", ""))
    confidence = payload.get("confidence")
    rec = payload.get("recommendation") or {}
    lines = [
        f"<b>Gold {decision}</b>",
        summary,
    ]
    if confidence is not None:
        lines.append(f"Confidence: {float(confidence) * 100:.0f}%")
    entry = rec.get("entry")
    sl = rec.get("stopLoss") or rec.get("stop_loss")
    targets = rec.get("targets") or []
    if entry is not None:
        lines.append(f"Entry: <code>{entry}</code>")
    if sl is not None:
        lines.append(f"SL: <code>{sl}</code>")
    if targets:
        lines.append("TP: " + " / ".join(f"<code>{t}</code>" for t in targets[:2]))
    lines.append("<i>Recommendations only — no execution.</i>")
    return "\n".join(lines)
