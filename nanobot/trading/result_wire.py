"""Serialize AgentFinalResult for WebUI agent_ui and tool responses."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from nanobot.trading.types import AgentFinalResult


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
    payload["recommendation"] = {
        "action": rec.action,
        "entry": rec.entry,
        "stopLoss": rec.stop_loss,
        "targets": rec.targets,
        "planType": d.plan_type,
        "executionState": d.execution_state,
    }
    return payload
