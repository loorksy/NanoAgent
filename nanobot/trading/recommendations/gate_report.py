"""Build gate_report artifacts from stored recommendation rows."""

from __future__ import annotations

import json
from typing import Any

from nanobot.trading.i18n import artifact_title, gate_label, tr
from nanobot.trading.locale import normalize_locale
from nanobot.trading.types import AgentFinalResult, AgentRecommendation, FinalDecisionResult


def _parse_gate_verdicts(raw: str | None) -> list[dict[str, Any]]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [row for row in data if isinstance(row, dict)]


def build_gate_report_artifact(
    row: dict[str, Any],
    *,
    locale: str = "en",
) -> dict[str, Any]:
    loc = normalize_locale(locale)
    verdicts = _parse_gate_verdicts(row.get("gate_json"))
    veto_id = None
    allowed = True
    wire_verdicts: list[dict[str, Any]] = []
    for item in verdicts:
        gate_id = str(item.get("id") or "")
        status = str(item.get("status") or "")
        reason = str(item.get("reason_ar") or item.get("reason") or "")
        if status in {"fail", "veto", "blocked"}:
            allowed = False
            if veto_id is None:
                veto_id = gate_id
        wire_verdicts.append(
            {
                "id": gate_id,
                "name": gate_label(gate_id, loc),
                "status": status,
                "reason": reason,
            }
        )
    return {
        "type": "gate_report",
        "title": artifact_title("gate_report", loc),
        "payload": {
            "allowed": allowed,
            "verdicts": wire_verdicts,
            "vetoedBy": veto_id,
            "recommendationId": row.get("id"),
            "direction": row.get("direction"),
        },
    }


def build_gate_report_result(
    row: dict[str, Any] | None,
    *,
    operator_text: str = "",
    locale: str = "en",
) -> AgentFinalResult:
    loc = normalize_locale(locale)
    if not row:
        decision = FinalDecisionResult(
            decision="wait",
            confidence=0.0,
            summary=tr("followup.no_live_plan", loc),
            key_reasons=["no live plan"],
            risk_warnings=[],
            recommendation=AgentRecommendation(action="wait"),
            execution_state="blocked",
            refusal_summary="no live plan",
        )
        return AgentFinalResult(decision=decision, team_mode="gate_report")

    artifact = build_gate_report_artifact(row, locale=loc)
    direction = str(row.get("direction") or "wait")
    allowed_key = "gate_report.allowed_yes" if artifact["payload"]["allowed"] else "gate_report.allowed_no"
    summary = tr(
        "gate_report.summary",
        loc,
        direction=direction.upper(),
        allowed=tr(allowed_key, loc),
    )
    decision = FinalDecisionResult(
        decision=direction if direction in ("buy", "sell") else "wait",
        confidence=float(row.get("confidence") or 0.5),
        summary=summary,
        key_reasons=[str(row.get("summary") or "")],
        risk_warnings=["Gate report from stored recommendation — synthesizer not called"],
        recommendation=AgentRecommendation(
            action=direction if direction in ("buy", "sell") else "wait",
            entry=float(row["entry"]) if row.get("entry") is not None else None,
            stop_loss=float(row["stop_loss"]) if row.get("stop_loss") is not None else None,
            targets=[float(t) for t in (row.get("targets") or [])],
            execution_state=str(row.get("status") or "valid_now"),
            interval=str(row.get("interval") or "15m"),
        ),
        execution_state=str(row.get("status") or "valid_now"),
    )
    result = AgentFinalResult(
        decision=decision,
        team_mode="gate_report",
        recommendation_id=str(row.get("id") or ""),
        artifacts=[artifact],
    )
    return result
