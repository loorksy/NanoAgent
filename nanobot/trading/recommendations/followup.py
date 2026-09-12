"""Follow-up helpers for stored gold recommendations."""

from __future__ import annotations

from nanobot.trading.recommendations.store import get_recommendation, list_recommendations


def latest_open_recommendation() -> dict | None:
    for row in list_recommendations(limit=5):
        if row.get("status") in {"valid_now", "awaiting_activation"}:
            return row
    return None


def explain_stored_recommendation(rec_id: str) -> str:
    row = get_recommendation(rec_id)
    if not row:
        return "No stored recommendation found for that id."
    direction = str(row.get("direction", "wait")).upper()
    entry = row.get("entry")
    sl = row.get("stop_loss")
    targets = row.get("targets") or []
    summary = row.get("summary", "")
    parts = [f"{direction} on XAUUSD — {summary}"]
    if entry is not None:
        parts.append(f"Entry: {entry}")
    if sl is not None:
        parts.append(f"Stop: {sl}")
    if targets:
        parts.append("Targets: " + " / ".join(str(t) for t in targets))
    return "\n".join(parts)
