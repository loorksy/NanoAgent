"""Agent-chosen trading artifacts (1–4 per turn) instead of a fixed card deck."""

from __future__ import annotations

from typing import Any

from nanobot.trading.cards.format import format_price, translate_reason
from nanobot.trading.intent_router import IntentKind
from nanobot.trading.locale import normalize_locale
from nanobot.trading.types import AgentFinalResult

_MAX_ARTIFACTS = 4

ARTIFACT_TYPES = frozenset(
    {
        "decision",
        "level_map",
        "gate_report",
        "chart_snapshot",
        "macro_dashboard",
        "key_reasons",
        "visual_review",
        "team_briefing",
        "tracked_plan",
    }
)

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


def parse_artifacts_requested(raw: Any) -> list[str]:
    """Normalize LLM artifact picks to a deduped list of allowed types."""
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw[:_MAX_ARTIFACTS]:
        kind = str(item or "").strip().lower().replace("-", "_")
        if kind in ARTIFACT_TYPES and kind not in out:
            out.append(kind)
    return out


def _title(kind: str, locale: str) -> str:
    loc = "ar" if normalize_locale(locale) == "ar" else "en"
    return _TITLES[loc].get(kind, kind)


def _build_artifact_pool(
    result: AgentFinalResult,
    *,
    intent_kind: IntentKind | str = "gold_analysis",
    locale: str = "en",
) -> dict[str, dict[str, Any]]:
    """Build every artifact that is available for this turn (may be empty)."""
    loc = normalize_locale(locale)
    d = result.decision
    rec = d.recommendation
    pool: dict[str, dict[str, Any]] = {}
    snapshots = list(result.visual_snapshots or [])

    if snapshots:
        frame = snapshots[0] if snapshots else None
        if isinstance(frame, dict) and (frame.get("image") or frame.get("dataUrl")):
            pool["chart_snapshot"] = {
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

    if d.decision in ("buy", "sell"):
        pool["decision"] = {
            "type": "decision",
            "title": _title("decision", loc),
            "payload": {
                "decision": d.decision,
                "summary": d.summary,
                "confidence": d.confidence,
            },
        }

    if (
        d.decision in ("buy", "sell")
        and rec.entry
        and rec.stop_loss
        and rec.targets
        and intent_kind in ("gold_analysis", "recommendation", "team_swarm")
    ):
        pool["level_map"] = {
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

    if d.gate_chain and (
        not d.gate_chain.allowed
        or intent_kind in ("gold_analysis", "recommendation", "team_swarm")
    ):
        pool["gate_report"] = {
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

    review = d.visual_review
    if review and review.state != "not_checked" and intent_kind != "price_query":
        if (
            review.state in {"checked", "partial"}
            and snapshots
            and "chart_snapshot" not in pool
        ):
            pool["chart_snapshot"] = {
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
        elif review.state in {"checked", "partial", "missing"}:
            pool["visual_review"] = {
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

    if result.macro_drivers and intent_kind in ("gold_analysis", "recommendation", "team_swarm"):
        pool["macro_dashboard"] = {
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

    if result.team_agents and intent_kind == "team_swarm":
        pool["team_briefing"] = {
            "type": "team_briefing",
            "title": _title("team_briefing", loc),
            "payload": {"agents": list(result.team_agents), "teamMode": result.team_mode},
        }

    if d.key_reasons:
        reasons = [
            translate_reason(str(r), locale=loc) for r in d.key_reasons[:5] if str(r).strip()
        ]
        if reasons:
            pool["key_reasons"] = {
                "type": "key_reasons",
                "title": _title("key_reasons", loc),
                "payload": {"reasons": reasons},
            }

    if result.recommendation_id and intent_kind == "gold_analysis":
        pool["tracked_plan"] = {
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

    return pool


def _default_artifact_order(
    pool: dict[str, dict[str, Any]],
    *,
    intent_kind: IntentKind | str = "gold_analysis",
) -> list[str]:
    """Deterministic fallback order (legacy behavior when the LLM picks nothing valid)."""
    order: list[str] = []
    for kind in (
        "decision",
        "level_map",
        "gate_report",
        "chart_snapshot",
        "visual_review",
        "macro_dashboard",
        "team_briefing",
        "key_reasons",
        "tracked_plan",
    ):
        if kind in pool:
            order.append(kind)
        if len(order) >= _MAX_ARTIFACTS:
            break
    if intent_kind == "team_swarm" and "team_briefing" in pool and "team_briefing" not in order:
        order = [*(order[: _MAX_ARTIFACTS - 1]), "team_briefing"]
    return order[:_MAX_ARTIFACTS]


def _resolve_selection(
    pool: dict[str, dict[str, Any]],
    *,
    requested: list[str] | None,
    intent_kind: IntentKind | str,
    decision: str,
) -> list[str]:
    """Merge LLM picks with mandatory fallbacks; fall back to deterministic order."""
    if intent_kind == "chart_image" and "chart_snapshot" in pool:
        return ["chart_snapshot"]

    normalized = parse_artifacts_requested(requested or [])
    if normalized:
        selection = [kind for kind in normalized if kind in pool]
        if decision in ("buy", "sell") and "decision" in pool and "decision" not in selection:
            selection.insert(0, "decision")
        if selection:
            return selection[:_MAX_ARTIFACTS]

    return _default_artifact_order(pool, intent_kind=intent_kind)


def emit_trading_artifacts(
    result: AgentFinalResult,
    *,
    intent_kind: IntentKind | str = "gold_analysis",
    locale: str = "en",
    chart_only: bool = False,
    requested: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Pick a small artifact set for this turn (LLM-requested when available)."""
    pool = _build_artifact_pool(result, intent_kind=intent_kind, locale=locale)

    if chart_only:
        if "chart_snapshot" in pool:
            return [pool["chart_snapshot"]]
        return []

    selection = _resolve_selection(
        pool,
        requested=requested,
        intent_kind=intent_kind,
        decision=str(result.decision.decision),
    )
    return [pool[kind] for kind in selection if kind in pool]
