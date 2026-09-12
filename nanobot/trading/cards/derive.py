"""Derive UI cards from AgentFinalResult — never LLM-authored."""

from __future__ import annotations

from typing import Any

from nanobot.trading.types import AgentFinalResult

CARD_ORDER = [
    "scenario_notice",
    "decision",
    "plan_levels",
    "activation",
    "invalidation",
    "gate_checklist",
    "visual_review",
    "key_reasons",
    "risk_warnings",
    "tracked_recommendation",
]


def derive_cards(result: AgentFinalResult) -> list[dict[str, Any]]:
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
        cards.append(
            {
                "kind": "invalidation",
                "stopLoss": rec.stop_loss,
                "summary": f"Invalidated if price reaches {rec.stop_loss}",
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
        cards.append(
            {
                "kind": "visual_review",
                "state": "not_checked",
                "timeframes": [result.market.interval if result.market else "15m"],
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
