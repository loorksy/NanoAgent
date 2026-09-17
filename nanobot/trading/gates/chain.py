"""Run the quality-check chain with short-circuit on a blocking veto."""

from __future__ import annotations

import time

from nanobot.trading.gates.build_gates import GATE_REQUIRED, GateDefinition
from nanobot.trading.i18n import tr
from nanobot.trading.types import GateChainResult, GateStatus, GateVerdict


async def run_gate_chain(gates: list[GateDefinition]) -> GateChainResult:
    verdicts: list[GateVerdict] = []
    confidence_delta = 0
    vetoed_by: GateVerdict | None = None

    for gate in gates:
        started = int(time.time() * 1000)
        try:
            raw = await gate.run()
        except Exception as exc:
            raw = {
                "status": "unavailable",
                "reason_key": "gate.internal_error",
                "reason": tr("gate.internal_error"),
                "reason_ar": tr("gate.internal_error", "ar"),
                "evidence": {"error_type": type(exc).__name__},
            }
        finished = int(time.time() * 1000)
        status: GateStatus = raw.get("status", "unavailable")
        delta = int(raw.get("confidence_delta", 0) or 0)
        verdict = GateVerdict(
            id=gate.id,  # type: ignore[arg-type]
            name=gate.name,
            status=status,
            reason=str(raw.get("reason") or raw.get("reason_ar") or ""),
            reason_ar=str(raw.get("reason_ar") or ""),
            evidence=raw.get("evidence"),
            confidence_delta=delta,
            started_at=started,
            finished_at=finished,
        )
        verdicts.append(verdict)
        confidence_delta += delta

        required = GATE_REQUIRED.get(gate.id, False)
        if status == "veto" or (status == "unavailable" and required):
            vetoed_by = verdict
            break
        if status == "warn":
            continue

    allowed = vetoed_by is None
    return GateChainResult(
        verdicts=verdicts,
        allowed=allowed,
        confidence_delta=confidence_delta,
        vetoed_by=vetoed_by,
    )
