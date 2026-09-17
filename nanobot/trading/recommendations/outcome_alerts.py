"""Outcome alerts when live recommendation status changes."""

from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Any

from nanobot.trading.cards.format import format_price
from nanobot.trading.i18n import label_map
from nanobot.trading.locale import locale_from_text, normalize_locale

ALERTABLE_OUTCOMES = frozenset({"in_trade", "tp1", "invalidated"})
# Price oscillation around entry should not spam alerts.
_OSCILLATION_PAIRS = frozenset({frozenset({"waiting", "in_trade"})})


@dataclass(frozen=True)
class OutcomeTransition:
    rec_id: str
    previous: str
    current: str
    row: dict[str, Any]


def should_alert_transition(transition: OutcomeTransition) -> bool:
    previous = transition.previous
    current = transition.current
    if current not in ALERTABLE_OUTCOMES or previous == current:
        return False
    if frozenset({previous, current}) in _OSCILLATION_PAIRS:
        return False
    return True


def _alert_locale(row: dict[str, Any], locale: str | None = None) -> str:
    if locale:
        return normalize_locale(locale)
    stored = row.get("locale")
    if isinstance(stored, str) and stored:
        return normalize_locale(stored)
    return locale_from_text(str(row.get("summary") or ""))


def transition_to_web_payload(
    transition: OutcomeTransition,
    *,
    live_price: float | None = None,
    locale: str | None = None,
) -> dict[str, Any]:
    status = transition.current
    loc = _alert_locale(transition.row, locale)
    return {
        "recommendationId": transition.rec_id,
        "previousStatus": transition.previous,
        "outcomeStatus": status,
        "direction": str(transition.row.get("direction") or "wait"),
        "locale": loc,
        "summary": format_outcome_alert(
            transition.row,
            status,
            live_price=live_price,
            html_mode=False,
            locale=loc,
        ),
        "livePrice": live_price,
    }


def format_outcome_alert(
    row: dict[str, Any],
    status: str,
    *,
    live_price: float | None = None,
    html_mode: bool = True,
    locale: str | None = None,
) -> str:
    loc = _alert_locale(row, locale)
    labels = label_map("outcome_field", loc)
    status_labels = label_map("outcome_status", loc)
    direction = str(row.get("direction") or "wait").upper()
    entry = row.get("entry")
    stop = row.get("stop_loss")
    targets = list(row.get("targets") or [])
    status_label = status_labels.get(status, status)
    summary = str(row.get("summary") or "").strip()

    if html_mode:
        lines = [
            f"<b>{html.escape(labels['title'])}</b>",
            f"{html.escape(labels['status'])}: <b>{html.escape(status_label)}</b> ({html.escape(direction)})",
        ]
        if live_price is not None:
            lines.append(f"{html.escape(labels['live'])}: <code>{format_price(live_price)}</code>")
        if entry is not None:
            lines.append(f"{html.escape(labels['entry'])}: <code>{format_price(entry)}</code>")
        if stop is not None:
            lines.append(f"{html.escape(labels['stop'])}: <code>{format_price(stop)}</code>")
        if targets:
            target_txt = " / ".join(format_price(t) for t in targets[:3])
            lines.append(f"{html.escape(labels['targets'])}: <code>{target_txt}</code>")
        if summary:
            lines.append(html.escape(summary))
        return "\n".join(lines)

    lines = [
        f"{labels['title']}",
        f"{labels['status']}: {status_label} ({direction})",
    ]
    if live_price is not None:
        lines.append(f"{labels['live']}: {format_price(live_price)}")
    if entry is not None:
        lines.append(f"{labels['entry']}: {format_price(entry)}")
    if stop is not None:
        lines.append(f"{labels['stop']}: {format_price(stop)}")
    if targets:
        lines.append(f"{labels['targets']}: " + " / ".join(format_price(t) for t in targets[:3]))
    if summary:
        lines.append(summary)
    return "\n".join(lines)
