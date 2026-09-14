"""Follow-up helpers — fresh candles and a status grade, never a second synthesizer."""

from __future__ import annotations

from typing import Any

from nanobot.trading.gold import DATA_SYMBOL
from nanobot.trading.i18n import label_map, tr
from nanobot.trading.locale import locale_from_text
from nanobot.trading.oanda import fetch_quote
from nanobot.trading.recommendations.outcome_alerts import OutcomeTransition
from nanobot.trading.recommendations.state_machine import (
    CLOSED_OUTCOME_STATUSES,
    LIVE_OUTCOME_STATUSES,
    can_transition,
    normalize_outcome_status,
)
from nanobot.trading.recommendations.store import (
    get_recommendation,
    list_recommendations,
    update_recommendation_status,
)
from nanobot.trading.types import AgentRecommendation, FinalDecisionResult

def finalize_live_plan_if_closed(
    row: dict[str, Any] | None,
    *,
    live_price: float | None = None,
) -> dict[str, Any] | None:
    """Persist terminal outcomes so a new recommendation can be issued."""
    if not row:
        return None
    current = normalize_outcome_status(str(row.get("status") or "valid_now"))
    graded = normalize_outcome_status(grade_outcome_status(row, live_price=live_price))
    if graded in CLOSED_OUTCOME_STATUSES and graded != current:
        update_recommendation_status(str(row["id"]), graded)
        return None
    if graded in CLOSED_OUTCOME_STATUSES:
        return None
    return row


def explain_new_rec_blocked(
    row: dict[str, Any] | None,
    *,
    operator_text: str = "",
    live_price: float | None = None,
) -> FinalDecisionResult:
    locale = locale_from_text(operator_text)
    if not row:
        return FinalDecisionResult(
            decision="wait",
            confidence=0.0,
            summary=tr("followup.no_live_plan", locale),
            key_reasons=[tr("followup.one_plan_rule", locale)],
            risk_warnings=[],
            recommendation=AgentRecommendation(action="wait"),
            execution_state="blocked",
            refusal_summary="no live plan",
        )
    direction = str(row.get("direction") or "wait")
    status = grade_outcome_status(row, live_price=live_price)
    direction_label = tr(f"direction.{direction.lower()}", locale)
    status_label = label_map("outcome_status", locale).get(status, status)
    entry = row.get("entry")
    stop = row.get("stop_loss")
    levels = ""
    if entry is not None and stop is not None:
        levels = tr(
            "followup.plan_levels",
            locale,
            entry=f"{float(entry):.2f}",
            stop=f"{float(stop):.2f}",
        )
    summary = tr(
        "followup.new_rec_blocked",
        locale,
        direction=direction_label,
        status=status_label,
        levels=levels,
    )
    return FinalDecisionResult(
        decision="wait",
        confidence=float(row.get("confidence") or 0.5),
        summary=summary,
        key_reasons=[tr("followup.one_plan_rule", locale)],
        risk_warnings=[tr("followup.kernel_not_chat", locale)],
        recommendation=AgentRecommendation(action="wait"),
        execution_state="blocked",
        refusal_summary=tr("followup.one_plan_rule", locale),
    )


def latest_open_recommendation() -> dict | None:
    for row in list_recommendations(limit=20):
        if row.get("status") in LIVE_OUTCOME_STATUSES:
            return row
    return None


def grade_outcome_status(
    row: dict[str, Any],
    *,
    live_price: float | None = None,
) -> str:
    direction = str(row.get("direction") or "wait")
    entry = row.get("entry")
    stop = row.get("stop_loss")
    targets = list(row.get("targets") or [])
    stored = normalize_outcome_status(str(row.get("status") or "valid_now"))
    if stored in CLOSED_OUTCOME_STATUSES:
        return stored
    if direction not in {"buy", "sell"} or entry is None or stop is None:
        return stored

    live = live_price
    if live is None:
        try:
            quote = fetch_quote(DATA_SYMBOL)
            live = quote.mid if quote else None
        except Exception:
            live = None
    if live is None:
        return stored

    if direction == "sell":
        if live >= float(stop):
            return "invalidated"
        if targets and live <= float(targets[0]):
            return "tp1"
        if live < float(entry):
            return "in_trade"
        return "waiting"
    if live <= float(stop):
        return "invalidated"
    if targets and live >= float(targets[0]):
        return "tp1"
    if live > float(entry):
        return "in_trade"
    return "waiting"


def refresh_recommendation_outcomes(
    *,
    live_price: float | None = None,
) -> tuple[dict[str, int], list[OutcomeTransition]]:
    """Grade open recommendations against live price and persist outcomes."""
    counts = {"updated": 0, "open": 0, "closed": 0}
    transitions: list[OutcomeTransition] = []
    for row in list_recommendations(limit=200):
        current = normalize_outcome_status(str(row.get("status") or "valid_now"))
        graded = normalize_outcome_status(grade_outcome_status(row, live_price=live_price))
        if graded != current and can_transition(current, graded):
            update_recommendation_status(str(row["id"]), graded)
            transitions.append(
                OutcomeTransition(
                    rec_id=str(row["id"]),
                    previous=current,
                    current=graded,
                    row={**row, "status": graded},
                )
            )
            counts["updated"] += 1
            current = graded
        if current in LIVE_OUTCOME_STATUSES:
            counts["open"] += 1
        elif current in CLOSED_OUTCOME_STATUSES:
            counts["closed"] += 1
    return counts, transitions


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


def grade_live_recommendation(
    row: dict | None,
    *,
    operator_text: str = "",
    live_price: float | None = None,
) -> FinalDecisionResult:
    locale = locale_from_text(operator_text)
    if not row:
        return FinalDecisionResult(
            decision="wait",
            confidence=0.0,
            summary=tr("followup.no_live_plan", locale),
            key_reasons=["no live plan"],
            risk_warnings=[],
            recommendation=AgentRecommendation(action="wait"),
            execution_state="blocked",
            refusal_summary="no live plan",
        )
    direction = str(row.get("direction") or "wait")
    entry = row.get("entry")
    stop = row.get("stop_loss")
    targets = list(row.get("targets") or [])
    live = live_price
    if live is None:
        try:
            quote = fetch_quote(DATA_SYMBOL)
            live = quote.mid if quote else None
        except Exception:
            live = None

    status = grade_outcome_status(row, live_price=live)
    notes: list[str] = []
    if live is not None and entry is not None and stop is not None:
        notes.append(f"live={live:.2f} entry={entry} sl={stop}")

    direction_label = tr(f"direction.{direction.lower()}", locale)
    status_label = label_map("outcome_status", locale).get(status, status)
    summary = tr(
        "followup.summary",
        locale,
        direction=direction_label,
        status=status_label,
    )
    rec = AgentRecommendation(
        action=direction if direction in ("buy", "sell") else "wait",
        entry=float(entry) if entry is not None else None,
        stop_loss=float(stop) if stop is not None else None,
        targets=[float(t) for t in targets],
        execution_state=str(row.get("status") or "valid_now"),
        interval=str(row.get("interval") or "15m"),
    )
    return FinalDecisionResult(
        decision=rec.action,
        confidence=float(row.get("confidence") or 0.5),
        summary=summary,
        key_reasons=notes or [str(row.get("summary") or "")],
        risk_warnings=["Follow-up only — synthesizer not called"],
        recommendation=rec,
        plan_type=None,
        execution_state=rec.execution_state,
    )
