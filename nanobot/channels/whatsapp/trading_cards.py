"""WhatsApp plain-text renderer for gold trading recommendation cards."""

from __future__ import annotations

from typing import Any


def render_recommendation_card(payload: dict[str, Any]) -> str:
    decision = str(payload.get("decision", "wait")).upper()
    summary = str(payload.get("summary", ""))
    confidence = payload.get("confidence")
    rec = payload.get("recommendation") or {}
    lines = [
        f"*Gold {decision}*",
        summary,
    ]
    if confidence is not None:
        lines.append(f"Confidence: {float(confidence) * 100:.0f}%")
    entry = rec.get("entry")
    sl = rec.get("stopLoss") or rec.get("stop_loss")
    targets = rec.get("targets") or []
    if entry is not None:
        lines.append(f"Entry: {entry}")
    if sl is not None:
        lines.append(f"SL: {sl}")
    if targets:
        lines.append("TP: " + " / ".join(str(t) for t in targets[:2]))
    lines.append("_Recommendations only — no execution._")
    return "\n".join(lines)
