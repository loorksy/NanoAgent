"""Agent-chosen trading artifacts (1–4 per turn) instead of a fixed card deck."""

from __future__ import annotations

from typing import Any

from nanobot.trading.cards.format import format_price, translate_reason
from nanobot.trading.intent_router import IntentKind
from nanobot.trading.locale import normalize_locale
from nanobot.trading.types import AgentFinalResult

_MAX_ARTIFACTS = 4

_TITLES = {
    "ar": {
        "decision": "القرار",
        "level_map": "مستويات الخطة",
        "gate_report": "تقرير البوابات",
        "chart_snapshot": "لقطة الشارت",
        "macro_dashboard": "محركات الاقتصاد الكلي",
        "key_reasons": "أهم الأسباب",
        "visual_review": "المراجعة البصرية",
        "team_briefing": "ملخص الفريق",
        "tracked_plan": "الخطة المتتبعة",
    },
    "en": {
        "decision": "Decision",
        "level_map": "Plan levels",
        "gate_report": "Gate report",
        "chart_snapshot": "Chart snapshot",
        "macro_dashboard": "Macro drivers",
        "key_reasons": "Key reasons",
        "visual_review": "Visual review",
        "team_briefing": "Team briefing",
        "tracked_plan": "Tracked plan",
    },
}


def _title(kind: str, locale: str) -> str:
    loc = "ar" if normalize_locale(locale) == "ar" else "en"
    return _TITLES[loc].get(kind, kind)


def emit_trading_artifacts(
    result: AgentFinalResult,
    *,
    intent_kind: IntentKind | str = "gold_analysis",
    locale: str = "en",
    chart_only: bool = False,
) -> list[dict[str, Any]]:
    """Pick a small artifact set for this turn (not the full CARD_ORDER deck)."""
    loc = normalize_locale(locale)
    d = result.decision
    rec = d.recommendation
    artifacts: list[dict[str, Any]] = []

    snapshots = list(result.visual_snapshots or [])
    if snapshots and (chart_only or intent_kind == "chart_image"):
        frame = snapshots[0] if snapshots else None
        if isinstance(frame, dict) and (frame.get("image") or frame.get("dataUrl")):
            artifacts.append(
                {
                    "type": "chart_snapshot",
                    "title": _title("chart_snapshot", loc),
                    "mime": "image/jpeg",
                    "payload": {
                        "interval": rec.interval if rec else "15m",
                        "timeframes": [
                            str(f.get("timeframe") or "")
                            for f in snapshots
                            if isinstance(f, dict)
                        ],
                        "image": frame.get("image") or frame.get("dataUrl"),
                    },
                }
            )
        if chart_only or intent_kind == "chart_image":
            return artifacts[:_MAX_ARTIFACTS]

    if d.decision in ("buy", "sell", "wait") and not chart_only:
        artifacts.append(
            {
                "type": "decision",
                "title": _title("decision", loc),
                "payload": {
                    "decision": d.decision,
                    "summary": d.summary,
                    "confidence": d.confidence,
                },
            }
        )

    if (
        d.decision in ("buy", "sell")
        and rec.entry
        and rec.stop_loss
        and rec.targets
        and intent_kind in ("gold_analysis", "recommendation", "team_swarm")
    ):
        artifacts.append(
            {
                "type": "level_map",
                "title": _title("level_map", loc),
                "payload": {
                    "direction": d.decision,
                    "entry": rec.entry,
                    "stopLoss": rec.stop_loss,
                    "targets": list(rec.targets),
                    "entryType": rec.entry_type,
                },
            }
        )

    if d.gate_chain and (
        not d.gate_chain.allowed
        or intent_kind in ("gold_analysis", "recommendation", "team_swarm")
    ):
        artifacts.append(
            {
                "type": "gate_report",
                "title": _title("gate_report", loc),
                "payload": {
                    "allowed": d.gate_chain.allowed,
                    "verdicts": [
                        {
                            "id": v.id,
                            "name": v.name,
                            "status": v.status,
                            "reason": v.reason_ar if loc == "ar" else v.reason_ar,
                        }
                        for v in d.gate_chain.verdicts
                    ],
                    "vetoedBy": d.gate_chain.vetoed_by.id if d.gate_chain.vetoed_by else None,
                },
            }
        )

    review = d.visual_review
    if (
        review
        and review.state in {"checked", "partial"}
        and snapshots
        and "chart_snapshot" not in {a["type"] for a in artifacts}
    ):
        artifacts.append(
            {
                "type": "chart_snapshot",
                "title": _title("chart_snapshot", loc),
                "mime": "image/jpeg",
                "payload": {
                    "state": review.state,
                    "notes": review.notes,
                    "image": snapshots[0].get("image") or snapshots[0].get("dataUrl")
                    if snapshots
                    else None,
                },
            }
        )
    elif review and review.state != "not_checked" and intent_kind != "price_query":
        artifacts.append(
            {
                "type": "visual_review",
                "title": _title("visual_review", loc),
                "payload": {
                    "state": review.state,
                    "requested": list(review.requested),
                    "captured": list(review.captured),
                    "missing": list(review.missing),
                    "notes": review.notes,
                },
            }
        )

    if result.macro_drivers and intent_kind in ("gold_analysis", "recommendation", "team_swarm"):
        artifacts.append(
            {
                "type": "macro_dashboard",
                "title": _title("macro_dashboard", loc),
                "payload": {
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
                },
            }
        )

    if result.team_agents and intent_kind == "team_swarm":
        artifacts.append(
            {
                "type": "team_briefing",
                "title": _title("team_briefing", loc),
                "payload": {"agents": list(result.team_agents), "teamMode": result.team_mode},
            }
        )

    if d.key_reasons and len(artifacts) < _MAX_ARTIFACTS:
        reasons = [
            translate_reason(str(r), locale=loc) for r in d.key_reasons[:5] if str(r).strip()
        ]
        if reasons:
            artifacts.append(
                {
                    "type": "key_reasons",
                    "title": _title("key_reasons", loc),
                    "payload": {"reasons": reasons},
                }
            )

    if result.recommendation_id and intent_kind == "gold_analysis":
        artifacts.append(
            {
                "type": "tracked_plan",
                "title": _title("tracked_plan", loc),
                "payload": {
                    "id": result.recommendation_id,
                    "direction": rec.action,
                    "status": rec.execution_state or "valid_now",
                    "symbol": rec.symbol,
                    "interval": rec.interval,
                    "entry": rec.entry,
                    "stopLoss": rec.stop_loss,
                    "targets": list(rec.targets or []),
                    "entryLabel": format_price(rec.entry) if rec.entry is not None else "",
                },
            }
        )

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for art in artifacts:
        kind = str(art.get("type") or "")
        if kind in seen:
            continue
        seen.add(kind)
        deduped.append(art)
        if len(deduped) >= _MAX_ARTIFACTS:
            break
    return deduped
