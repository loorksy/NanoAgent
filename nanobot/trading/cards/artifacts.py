"""Agent-chosen trading artifacts (1–4 per turn) instead of a fixed card deck."""

from __future__ import annotations

from typing import Any

from nanobot.trading.cards.format import format_price, translate_reason
from nanobot.trading.i18n import artifact_title
from nanobot.trading.intent_router import IntentKind
from nanobot.trading.locale import normalize_locale
from nanobot.trading.operator_keywords import (
    _GATE_KEYWORDS,
    _LEVEL_KEYWORDS,
    _STATUS_KEYWORDS,
)
from nanobot.trading.recommendations.followup import grade_outcome_status
from nanobot.trading.types import AgentFinalResult

_ANALYSIS_INTENTS = frozenset({"gold_analysis", "recommendation", "team_swarm", "recommendation_followup"})

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
        "price_quote",
        "plan_status",
    }
)

def infer_operator_artifacts(
    operator_text: str,
    intent_kind: IntentKind | str,
    *,
    followup: bool = False,
    has_live_plan: bool = False,
) -> list[str]:
    """Infer artifact picks for non-synthesizer paths (price, follow-up, specialist)."""
    text = operator_text or ""

    if intent_kind == "price_query":
        return ["price_quote"]

    if intent_kind == "chart_image":
        return ["chart_snapshot"]

    if followup or intent_kind == "recommendation_followup" or (
        has_live_plan and intent_kind in ("gold_analysis", "recommendation")
    ):
        if _LEVEL_KEYWORDS.search(text):
            return ["level_map", "plan_status"]
        if _STATUS_KEYWORDS.search(text):
            return ["plan_status", "tracked_plan"]
        return ["plan_status", "level_map"]

    if _GATE_KEYWORDS.search(text):
        return ["gate_report", "decision"]

    return []


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


def build_price_quote_artifact(
    quote: dict[str, Any],
    *,
    locale: str = "en",
) -> dict[str, Any]:
    """Standalone price artifact for get_gold_quote / fast-path price responses."""
    loc = normalize_locale(locale)
    return {
        "type": "price_quote",
        "title": artifact_title("price_quote", loc),
        "payload": {
            "symbol": str(quote.get("symbol") or "XAUUSD"),
            "bid": quote.get("bid"),
            "ask": quote.get("ask"),
            "mid": quote.get("mid"),
            "tradeable": bool(quote.get("tradeable")),
        },
    }


def build_price_quote_artifacts(
    quote: dict[str, Any],
    *,
    locale: str = "en",
) -> list[dict[str, Any]]:
    return [build_price_quote_artifact(quote, locale=locale)]


def _build_artifact_pool(
    result: AgentFinalResult,
    *,
    intent_kind: IntentKind | str = "gold_analysis",
    locale: str = "en",
    quote_data: dict[str, Any] | None = None,
    plan_row: dict[str, Any] | None = None,
    plan_status: str | None = None,
    live_price: float | None = None,
) -> dict[str, dict[str, Any]]:
    """Build every artifact that is available for this turn (may be empty)."""
    loc = normalize_locale(locale)
    d = result.decision
    rec = d.recommendation
    pool: dict[str, dict[str, Any]] = {}
    snapshots = list(result.visual_snapshots or [])

    if quote_data:
        pool["price_quote"] = build_price_quote_artifact(quote_data, locale=loc)

    if plan_row and intent_kind in _ANALYSIS_INTENTS:
        graded = plan_status or grade_outcome_status(plan_row, live_price=live_price)
        pool["plan_status"] = {
            "type": "plan_status",
            "title": artifact_title("plan_status", loc),
            "payload": {
                "id": str(plan_row.get("id") or result.recommendation_id or ""),
                "direction": str(plan_row.get("direction") or rec.action or "wait"),
                "status": graded,
                "livePrice": live_price,
                "entry": plan_row.get("entry"),
                "stopLoss": plan_row.get("stop_loss"),
                "targets": list(plan_row.get("targets") or []),
                "summary": d.summary,
            },
        }

    if snapshots:
        frame = snapshots[0] if snapshots else None
        if isinstance(frame, dict) and (frame.get("image") or frame.get("dataUrl")):
            pool["chart_snapshot"] = {
                "type": "chart_snapshot",
                "title": artifact_title("chart_snapshot", loc),
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
            "title": artifact_title("decision", loc),
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
        and intent_kind in _ANALYSIS_INTENTS
    ):
        pool["level_map"] = {
            "type": "level_map",
            "title": artifact_title("level_map", loc),
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
            "title": artifact_title("gate_report", loc),
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
                "title": artifact_title("chart_snapshot", loc),
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
                "title": artifact_title("visual_review", loc),
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
            "title": artifact_title("macro_dashboard", loc),
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
            "title": artifact_title("team_briefing", loc),
            "payload": {"agents": list(result.team_agents), "teamMode": result.team_mode},
        }

    if d.key_reasons:
        reasons = [
            translate_reason(str(r), locale=loc) for r in d.key_reasons[:5] if str(r).strip()
        ]
        if reasons:
            pool["key_reasons"] = {
                "type": "key_reasons",
                "title": artifact_title("key_reasons", loc),
                "payload": {"reasons": reasons},
            }

    if result.recommendation_id and intent_kind in ("gold_analysis", "recommendation_followup"):
        pool["tracked_plan"] = {
            "type": "tracked_plan",
            "title": artifact_title("tracked_plan", loc),
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

    if intent_kind == "price_query" and "price_quote" in pool:
        return ["price_quote"]

    normalized = parse_artifacts_requested(requested or [])
    if normalized:
        selection = [kind for kind in normalized if kind in pool]
        if decision in ("buy", "sell") and "decision" in pool and "decision" not in selection:
            selection.insert(0, "decision")
        if intent_kind == "recommendation_followup" and not selection:
            selection = [k for k in ("plan_status", "level_map", "tracked_plan") if k in pool]
        if selection:
            return selection[:_MAX_ARTIFACTS]

    if intent_kind == "recommendation_followup":
        followup_default = [k for k in ("plan_status", "level_map", "tracked_plan") if k in pool]
        if followup_default:
            return followup_default[:_MAX_ARTIFACTS]

    return _default_artifact_order(pool, intent_kind=intent_kind)


def emit_trading_artifacts(
    result: AgentFinalResult,
    *,
    intent_kind: IntentKind | str = "gold_analysis",
    locale: str = "en",
    chart_only: bool = False,
    requested: list[str] | None = None,
    quote_data: dict[str, Any] | None = None,
    plan_row: dict[str, Any] | None = None,
    plan_status: str | None = None,
    live_price: float | None = None,
) -> list[dict[str, Any]]:
    """Pick a small artifact set for this turn (LLM-requested when available)."""
    pool = _build_artifact_pool(
        result,
        intent_kind=intent_kind,
        locale=locale,
        quote_data=quote_data,
        plan_row=plan_row,
        plan_status=plan_status,
        live_price=live_price,
    )

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


def apply_result_artifacts(
    result: AgentFinalResult,
    *,
    operator_text: str,
    intent_kind: IntentKind | str,
    locale: str,
    followup: bool = False,
    quote_data: dict[str, Any] | None = None,
    plan_row: dict[str, Any] | None = None,
    plan_status: str | None = None,
    live_price: float | None = None,
) -> None:
    """Attach artifacts using synthesizer picks or operator-intent inference."""
    requested = list(result.decision.artifacts_requested or [])
    if not requested:
        requested = infer_operator_artifacts(
            operator_text,
            intent_kind,
            followup=followup,
            has_live_plan=bool(result.recommendation_id or plan_row),
        )
    result.artifacts = emit_trading_artifacts(
        result,
        intent_kind=intent_kind,
        locale=locale,
        requested=requested or None,
        quote_data=quote_data,
        plan_row=plan_row,
        plan_status=plan_status,
        live_price=live_price,
    )
