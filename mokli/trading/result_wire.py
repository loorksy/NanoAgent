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


_MODEL_KEYS = (
    "decision",
    "confidence",
    "summary",
    "keyReasons",
    "riskWarnings",
    "refusalSummary",
    "agreement",
    "dataSources",
    "teamMode",
    "recommendationId",
    "interval",
)
_MODEL_RECOMMENDATION_KEYS = (
    "action",
    "entry",
    "entryZone",
    "stopLoss",
    "targets",
    "takeProfit",
    "rr",
    "netRr",
    "riskPercent",
    "invalidationRule",
    "validityCandles",
    "activationCondition",
    "alternativeScenario",
)


def brief_for_model(wire: dict[str, Any], *, include_gates: bool = False) -> dict[str, Any]:
    """Structured decision for the model, without chart images or raw role transcripts."""
    brief: dict[str, Any] = {}
    for key in _MODEL_KEYS:
        value = wire.get(key)
        if value not in (None, "", [], {}):
            brief[key] = value
    recommendation = wire.get("recommendation")
    if isinstance(recommendation, dict):
        slim = {
            key: recommendation[key]
            for key in _MODEL_RECOMMENDATION_KEYS
            if key in recommendation and recommendation[key] not in (None, "", [])
        }
        if slim:
            brief["recommendation"] = slim
    agents = wire.get("teamAgents")
    if isinstance(agents, list):
        rows: list[dict[str, Any]] = []
        for row in agents:
            if not isinstance(row, dict):
                continue
            item: dict[str, Any] = {
                "agentId": row.get("agentId"),
                "role": row.get("role"),
                "status": row.get("status"),
            }
            match = _STANCE.search(str(row.get("summary") or ""))
            if match is not None:
                item["stance"] = match.group(1).lower()
            rows.append({key: value for key, value in item.items() if value not in (None, "")})
        if rows:
            brief["teamAgents"] = rows
    if include_gates:
        chain = wire.get("gateChain")
        if isinstance(chain, dict):
            verdicts = [
                {
                    "id": row.get("id"),
                    "name": row.get("name"),
                    "status": row.get("status"),
                }
                for row in chain.get("verdicts") or []
                if isinstance(row, dict)
            ]
            brief["gateChain"] = {"allowed": chain.get("allowed"), "verdicts": verdicts}
    return brief


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def decision_card_payload(result: Any) -> dict[str, Any] | None:
    """Structured decision for the client, using only fields the kernel returned.

    Missing levels stay null or are omitted. A result that is not a verdict
    returns None so a live-plan refusal and a stub do not become a card.
    """
    decision = getattr(result, "decision", None)
    verdict = getattr(decision, "decision", None)
    if verdict not in {"buy", "sell", "wait"}:
        return None
    reasons = [
        item
        for item in (getattr(decision, "key_reasons", None) or [])
        if isinstance(item, str) and item.strip()
    ]
    passed: list[str] = []
    blockers: list[str] = []
    chain = getattr(decision, "gate_chain", None)
    for verdict_row in getattr(chain, "verdicts", None) or []:
        status = getattr(verdict_row, "status", None)
        gate_id = str(getattr(verdict_row, "id", "") or "")
        if not gate_id:
            continue
        if status == "pass":
            passed.append(gate_id)
        elif status == "veto":
            reason = str(getattr(verdict_row, "reason", "") or "").strip()
            blockers.append(reason or gate_id)
    rec = getattr(decision, "recommendation", None)
    targets = [
        number
        for number in (_number(item) for item in (getattr(rec, "targets", None) or []))
        if number is not None
    ]
    confidence = _number(getattr(decision, "confidence", None))
    if confidence is None or not 0 <= confidence <= 1:
        confidence = None
    payload: dict[str, Any] = {
        "verdict": verdict,
        "entry": _number(getattr(rec, "entry", None)),
        "stop": _number(getattr(rec, "stop_loss", None)),
        "targets": targets,
        "confidence": confidence,
        "reasons": reasons,
        "gates_passed": passed,
    }
    summary = getattr(decision, "summary", None)
    if isinstance(summary, str) and summary.strip():
        payload["summary"] = summary.strip()
    plan_id = getattr(result, "recommendation_id", None)
    if isinstance(plan_id, str) and plan_id:
        payload["plan_id"] = plan_id
    zone = getattr(rec, "entry_zone", None)
    low = _number(getattr(zone, "low", None))
    high = _number(getattr(zone, "high", None))
    if low is not None and high is not None:
        payload["entry_zone"] = {"low": low, "high": high}
    risk_pct = _risk_percent(decision)
    # Gate evidence stores a fraction of balance. The decision card uses the
    # same percent-point scale as the risk card (1 means 1%).
    if risk_pct is not None:
        payload["risk_pct"] = risk_pct * 100 if risk_pct <= 1 else risk_pct
    rr = _number(getattr(rec, "rr", None))
    if rr is not None:
        payload["rr"] = rr
    net_rr = _number(getattr(rec, "net_rr", None))
    if net_rr is not None:
        payload["net_rr"] = net_rr
    agreement = _agreement(list(getattr(result, "team_agents", None) or []))
    if agreement is not None:
        payload["agreement"] = agreement
    invalidation = getattr(rec, "invalidation_rule", None)
    if isinstance(invalidation, str) and invalidation.strip():
        payload["invalidation"] = invalidation.strip()
    validity = getattr(rec, "validity_candles", None)
    if isinstance(validity, int) and not isinstance(validity, bool):
        payload["validity_candles"] = validity
    alternative = getattr(rec, "alternative_scenario", None)
    if isinstance(alternative, str) and alternative.strip():
        payload["alternative"] = alternative.strip()
    market = getattr(result, "market", None)
    symbol = getattr(market, "symbol", None)
    interval = getattr(market, "interval", None)
    if isinstance(symbol, str) and symbol and isinstance(interval, str) and interval:
        payload["data_sources"] = [f"market:{symbol}:{interval}"]
    if blockers:
        payload["blockers"] = blockers
    return payload
