"""Serialize AgentFinalResult for WebUI agent_ui and tool responses."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from nanobot.trading.types import AgentFinalResult


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    return None


def result_to_wire(result: AgentFinalResult) -> dict[str, Any]:
    d = result.decision
    payload: dict[str, Any] = {
        "decision": d.decision,
        "confidence": d.confidence,
        "summary": d.summary,
        "keyReasons": d.key_reasons,
        "riskWarnings": d.risk_warnings,
        "recommendationId": result.recommendation_id,
        "cards": result.cards,
        "stages": result.stages,
        "teamMode": result.team_mode,
        "teamAgents": list(result.team_agents or []),
        "macroDrivers": list(result.macro_drivers or []),
        "drawings": [asdict(x) for x in result.drawings],
        "interval": d.recommendation.interval if d.recommendation else "15m",
    }
    if d.gate_chain:
        payload["gateChain"] = {
            "allowed": d.gate_chain.allowed,
            "confidenceDelta": d.gate_chain.confidence_delta,
            "verdicts": [asdict(v) for v in d.gate_chain.verdicts],
        }
    if d.refusal_summary:
        payload["refusalSummary"] = d.refusal_summary
    rec = d.recommendation
    zone = getattr(rec, "entry_zone", None)
    try:
        entry_zone = {"low": float(zone.low), "high": float(zone.high)} if zone is not None else None
    except (TypeError, ValueError, AttributeError):
        entry_zone = None
    roles = getattr(rec, "timeframe_roles", None)
    try:
        timeframe_roles = {
            "lead": str(roles.lead),
            "context": str(roles.context),
            "timing": str(roles.timing),
        } if roles is not None else None
    except (TypeError, AttributeError):
        timeframe_roles = None

    def _path(rows: Any) -> list[dict[str, Any]]:
        if not isinstance(rows, (list, tuple)):
            return []
        out: list[dict[str, Any]] = []
        for item in rows:
            try:
                out.append(
                    {
                        "barsAhead": int(item.bars_ahead),
                        "price": float(item.price),
                        "label": str(getattr(item, "label", "")),
                    }
                )
            except (TypeError, ValueError, AttributeError):
                continue
        return out

    payload["recommendation"] = {
        "action": rec.action,
        "entry": rec.entry,
        "entryZone": entry_zone,
        "entryType": getattr(rec, "entry_type", None),
        "stopLoss": rec.stop_loss,
        "targets": rec.targets,
        "takeProfit": getattr(rec, "take_profit", None),
        "planType": getattr(rec, "plan_type", None) or d.plan_type,
        "executionState": getattr(rec, "execution_state", None) or d.execution_state,
        "activationCondition": getattr(rec, "activation_condition", None),
        "activationRule": getattr(rec, "activation_rule", None),
        "invalidationRule": getattr(rec, "invalidation_rule", None),
        "alternativeScenario": getattr(rec, "alternative_scenario", None),
        "validityCandles": getattr(rec, "validity_candles", None),
        "timeframeRoles": timeframe_roles,
        "scenarioPath": _path(getattr(rec, "scenario_path", None)),
        "alternativeScenarioPath": _path(getattr(rec, "alternative_scenario_path", None)),
        "rr": getattr(rec, "rr", None),
        "netRr": getattr(rec, "net_rr", None),
    }
    review = getattr(d, "visual_review", None)
    if review is not None:
        try:
            payload["visualReview"] = {
                "state": str(review.state),
                "requested": list(review.requested),
                "captured": list(review.captured),
                "missing": list(review.missing),
                "notes": str(review.notes),
            }
        except (TypeError, AttributeError):
            pass
    return _jsonable(payload)
