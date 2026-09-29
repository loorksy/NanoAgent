"""Serialize AgentFinalResult for Mokli agent_ui and tool responses."""

from __future__ import annotations

import re
from dataclasses import asdict
from typing import Any

from mokli.agent.tools.context import current_request_context
from mokli.trading.explain import build_trading_explain
from mokli.trading.locale import active_locale
from mokli.trading.types import AgentFinalResult

_STANCE = re.compile(r"(?im)^STANCE:\s*(buy|sell|wait)\s*$")


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    return None


def _risk_percent(decision: Any) -> float | None:
    chain = getattr(decision, "gate_chain", None)
    verdicts = getattr(chain, "verdicts", None) or []
    for verdict in verdicts:
        evidence = getattr(verdict, "evidence", None)
        if not isinstance(evidence, dict):
            continue
        value = evidence.get("risk_pct")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        return float(value)
    return None


def _agreement(agents: list[Any]) -> dict[str, Any] | None:
    """Count explicit STANCE lines. Missing lines omit the score instead of guessing."""
    done = [row for row in agents if isinstance(row, dict) and row.get("status") == "done"]
    if len(done) < 2:
        return None
    votes: list[str] = []
    for row in done:
        match = _STANCE.search(str(row.get("summary") or ""))
        if match is None:
            return None
        votes.append(match.group(1).lower())
    stance = max(set(votes), key=votes.count)
    return {"stance": stance, "agreeing": votes.count(stance), "votes": len(votes)}


def _data_sources(result: AgentFinalResult) -> list[str]:
    sources: list[str] = []
    market = result.market
    if market is not None:
        sources.append(f"market:{market.symbol}:{market.interval}")
    for stage in result.stages or []:
        if isinstance(stage, dict) and stage.get("stage"):
            sources.append(str(stage["stage"]))
    return sources


def result_to_wire(result: AgentFinalResult) -> dict[str, Any]:
    ctx = current_request_context()
    operator_text = (ctx.original_user_text if ctx else "") or ""
    d = result.decision
    payload: dict[str, Any] = {
        "locale": active_locale(operator_text),
        "decision": d.decision,
        "confidence": d.confidence,
        "summary": d.summary,
        "keyReasons": d.key_reasons,
        "riskWarnings": d.risk_warnings,
        "recommendationId": result.recommendation_id,
        "cards": result.cards,
        "artifacts": list(result.artifacts or []),
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
    risk_percent = _risk_percent(d)
    if risk_percent is not None:
        payload["recommendation"]["riskPercent"] = risk_percent
    sources = _data_sources(result)
    if sources:
        payload["dataSources"] = sources
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
    snapshots = getattr(result, "visual_snapshots", None) or []
    if snapshots:
        payload["chartSnapshots"] = [
            {
                "timeframe": str(frame.get("timeframe") or ""),
                "image": frame.get("image") or frame.get("dataUrl"),
                "context": frame.get("context"),
            }
            for frame in snapshots
            if isinstance(frame, dict)
        ]
    agreement = _agreement(list(result.team_agents or []))
    if agreement is not None:
        payload["agreement"] = agreement
    payload["operatorSummary"] = build_trading_explain(payload, locale=str(payload.get("locale") or "en"))
    return _jsonable(payload)
