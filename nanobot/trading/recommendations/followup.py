"""Follow-up helpers — fresh candles and a status grade, never a second synthesizer."""

from __future__ import annotations

import re

from nanobot.trading.gold import DATA_SYMBOL
from nanobot.trading.oanda import fetch_quote
from nanobot.trading.recommendations.store import get_recommendation, list_recommendations
from nanobot.trading.types import AgentRecommendation, FinalDecisionResult

_ARABIC_RE = re.compile(r"[\u0600-\u06FF]")


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


def grade_live_recommendation(
    row: dict | None,
    *,
    operator_text: str = "",
    live_price: float | None = None,
) -> FinalDecisionResult:
    arabic = bool(_ARABIC_RE.search(operator_text or ""))
    if not row:
        summary = "لا توجد توصية حيّة." if arabic else "No live recommendation."
        return FinalDecisionResult(
            decision="wait",
            confidence=0.0,
            summary=summary,
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

    status = "open"
    notes: list[str] = []
    if live is not None and entry is not None and stop is not None:
        if direction == "sell":
            if live >= float(stop):
                status = "invalidated"
            elif targets and live <= float(targets[0]):
                status = "tp1"
            elif live < float(entry):
                status = "in_trade"
            else:
                status = "waiting"
        elif direction == "buy":
            if live <= float(stop):
                status = "invalidated"
            elif targets and live >= float(targets[0]):
                status = "tp1"
            elif live > float(entry):
                status = "in_trade"
            else:
                status = "waiting"
        notes.append(f"live={live:.2f} entry={entry} sl={stop}")

    if arabic:
        summary = (
            f"التوصية الحيّة ما زالت {direction.upper()}. "
            f"التقييم: {status}. هذه متابعة — ليست توصية جديدة."
        )
        if "توصية جديدة" in operator_text or "حلل" in operator_text:
            summary += " لا يمكن إصدار توصية ثانية بينما الخطة الحالية حيّة."
    else:
        summary = (
            f"Live plan remains {direction.upper()}. "
            f"Status: {status}. This is a follow-up, not a new recommendation."
        )
        if "recommend" in operator_text.lower() or "analy" in operator_text.lower():
            summary += " A second recommendation is not issued while this plan is live."

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
