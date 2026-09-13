"""Arabic-first outcome alerts when live recommendation status changes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import html

from nanobot.trading.cards.format import format_price

ALERTABLE_OUTCOMES = frozenset({"in_trade", "tp1", "invalidated"})

_STATUS_AR = {
    "waiting": "بانتظار التفعيل",
    "in_trade": "داخل الصفقة",
    "tp1": "هدف 1 تحقق",
    "invalidated": "أُبطلت (وقف الخسارة)",
    "valid_now": "سارية",
    "awaiting_activation": "بانتظار التفعيل",
    "expired": "منتهية",
}


@dataclass(frozen=True)
class OutcomeTransition:
    rec_id: str
    previous: str
    current: str
    row: dict[str, Any]


def should_alert_transition(transition: OutcomeTransition) -> bool:
    return transition.current in ALERTABLE_OUTCOMES and transition.previous != transition.current


def transition_to_web_payload(
    transition: OutcomeTransition,
    *,
    live_price: float | None = None,
) -> dict[str, Any]:
    status = transition.current
    return {
        "recommendationId": transition.rec_id,
        "previousStatus": transition.previous,
        "outcomeStatus": status,
        "direction": str(transition.row.get("direction") or "wait"),
        "summary": format_outcome_alert(
            transition.row,
            status,
            live_price=live_price,
            html_mode=False,
        ),
        "livePrice": live_price,
    }


def format_outcome_alert(
    row: dict[str, Any],
    status: str,
    *,
    live_price: float | None = None,
    html_mode: bool = True,
) -> str:
    direction = str(row.get("direction") or "wait").upper()
    entry = row.get("entry")
    stop = row.get("stop_loss")
    targets = list(row.get("targets") or [])
    status_ar = _STATUS_AR.get(status, status)
    summary = str(row.get("summary") or "").strip()

    if html_mode:
        lines = [
            f"📣 <b>تحديث توصية الذهب ({html.escape(direction)})</b>",
            f"الحالة: <b>{html.escape(status_ar)}</b>",
        ]
        if live_price is not None:
            lines.append(f"السعر الحي: <b>{html.escape(format_price(live_price))}</b>")
        if entry is not None:
            lines.append(f"الدخول: {html.escape(format_price(entry))}")
        if stop is not None:
            lines.append(f"الوقف: {html.escape(format_price(stop))}")
        if targets:
            lines.append(
                "الأهداف: "
                + " / ".join(html.escape(format_price(target)) for target in targets[:3])
            )
        if summary:
            lines.append("")
            lines.append(html.escape(summary[:400]))
        return "\n".join(lines)

    lines = [
        f"📣 تحديث توصية الذهب ({direction})",
        f"الحالة: {status_ar}",
    ]
    if live_price is not None:
        lines.append(f"السعر الحي: {format_price(live_price)}")
    if entry is not None:
        lines.append(f"الدخول: {format_price(entry)}")
    if stop is not None:
        lines.append(f"الوقف: {format_price(stop)}")
    if targets:
        lines.append("الأهداف: " + " / ".join(format_price(target) for target in targets[:3]))
    if summary:
        lines.append(summary[:400])
    return "\n".join(lines)
