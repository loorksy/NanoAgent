"""Derive UI cards from AgentFinalResult — never LLM-authored."""

from __future__ import annotations

from typing import Any

from nanobot.trading.locale import normalize_locale
from nanobot.trading.types import AgentFinalResult

CARD_ORDER = [
    "scenario_notice",
    "decision",
    "plan_levels",
    "activation",
    "invalidation",
    "gate_checklist",
    "visual_review",
    "macro_drivers",
    "key_reasons",
    "risk_warnings",
    "tracked_recommendation",
]


def derive_cards(result: AgentFinalResult, *, locale: str = "en") -> list[dict[str, Any]]:
    loc = normalize_locale(locale)
    cards: list[dict[str, Any]] = []
    d = result.decision
    rec = d.recommendation

    cards.append(
        {
            "kind": "decision",
            "decision": d.decision,
            "summary": d.summary,
            "confidence": d.confidence,
        }
    )

    if d.decision in ("buy", "sell") and rec.entry and rec.stop_loss and rec.targets:
        cards.append(
            {
                "kind": "plan_levels",
                "direction": d.decision,
                "entry": rec.entry,
                "stopLoss": rec.stop_loss,
                "targets": rec.targets,
                "entryType": rec.entry_type,
            }
        )
        cards.append(
            {
                "kind": "activation",
                "planType": d.plan_type or "immediate",
                "executionState": d.execution_state or "valid_now",
            }
        )
        invalidation = (
            f"يبطل إذا وصل السعر إلى {rec.stop_loss}"
            if loc == "ar"
            else f"Invalidated if price reaches {rec.stop_loss}"
        )
        cards.append(
            {
                "kind": "invalidation",
                "stopLoss": rec.stop_loss,
                "summary": invalidation,
            }
        )

    if d.gate_chain:
        cards.append(
            {
                "kind": "gate_checklist",
                "allowed": d.gate_chain.allowed,
                "verdicts": [
                    {"id": v.id, "name": v.name, "status": v.status, "reason": v.reason_ar}
                    for v in d.gate_chain.verdicts
                ],
                "vetoedBy": d.gate_chain.vetoed_by.id if d.gate_chain.vetoed_by else None,
            }
        )

    if d.decision in ("buy", "sell"):
        review = d.visual_review
        cards.append(
            {
                "kind": "visual_review",
                "state": review.state if review else "not_checked",
                "timeframes": review.requested
                if review
                else [result.market.interval if result.market else "15m"],
                "missing": review.missing if review else [],
                "notes": review.notes if review else "",
            }
        )

    if result.macro_drivers:
        cards.append(
            {
                "kind": "macro_drivers",
                "drivers": [
                    {
                        "name": str(item.get("driver") or ""),
                        "bias": str(item.get("bias") or "neutral"),
                        "strength": item.get("strength"),
                        "one_line_rationale": str(item.get("one_line_rationale") or ""),
                        "ran": bool(item.get("ran")),
                        "reason": str(item.get("reason") or ""),
                    }
                    for item in result.macro_drivers
                    if isinstance(item, dict)
                ],
            }
        )

    if d.key_reasons:
        cards.append({"kind": "key_reasons", "reasons": d.key_reasons})
    if d.risk_warnings:
        cards.append({"kind": "risk_warnings", "warnings": d.risk_warnings})
    if result.recommendation_id:
        cards.append(
            {
                "kind": "tracked_recommendation",
                "id": result.recommendation_id,
                "status": rec.execution_state or "valid_now",
                "direction": rec.action,
                "symbol": rec.symbol,
                "interval": rec.interval,
            }
        )

    order_index = {k: i for i, k in enumerate(CARD_ORDER)}
    cards.sort(key=lambda c: order_index.get(c["kind"], 99))
    return cards
