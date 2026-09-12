"""G7 reprice loop — re-run risk gates after live re-anchor."""

from __future__ import annotations

from nanobot.trading.gates.build_gates import GateDefinition
from nanobot.trading.gates.chain import run_gate_chain
from nanobot.trading.types import AgentRecommendation, EntryPlan, GateChainResult, GateVerdict


MAX_REPRICE_ROUNDS = 2


def _merge_gate_chains(first: GateChainResult, second: GateChainResult) -> GateChainResult:
    replaced: dict[str, GateVerdict] = {v.id: v for v in first.verdicts}
    for verdict in second.verdicts:
        replaced[verdict.id] = verdict
    verdicts = list(replaced.values())
    confidence_delta = sum(v.confidence_delta for v in verdicts)
    vetoed = next((v for v in verdicts if v.status == "veto"), None)
    return GateChainResult(
        verdicts=verdicts,
        allowed=vetoed is None,
        confidence_delta=confidence_delta,
        vetoed_by=vetoed,
    )


async def apply_g7_reprice_loop(
    chain: GateChainResult,
    gates: list[GateDefinition],
    plan: EntryPlan,
    recommendation: AgentRecommendation,
) -> tuple[GateChainResult, EntryPlan, AgentRecommendation]:
    """When G7 re-anchors entry to live price, re-run G6→G7 up to N times."""
    current = chain
    gate_by_id = {gate.id: gate for gate in gates}
    g6 = gate_by_id.get("G6")
    g7 = gate_by_id.get("G7")
    if g6 is None or g7 is None:
        return current, plan, recommendation

    for _ in range(MAX_REPRICE_ROUNDS):
        g7_verdict = next((v for v in current.verdicts if v.id == "G7"), None)
        evidence = g7_verdict.evidence if g7_verdict else None
        if not isinstance(evidence, dict):
            break
        reanchored = evidence.get("reanchored_entry")
        if reanchored is None:
            break
        try:
            new_entry = float(reanchored)
        except (TypeError, ValueError):
            break
        plan.entry = new_entry
        recommendation.entry = new_entry
        recommendation.plan_type = "immediate"
        recommendation.entry_type = "market"
        recommendation.activation_rule = None
        recommendation.activation_condition = None
        recommendation.execution_state = "valid_now"
        follow_up = await run_gate_chain([g6, g7])
        current = _merge_gate_chains(current, follow_up)
        if not current.allowed:
            break
    return current, plan, recommendation
