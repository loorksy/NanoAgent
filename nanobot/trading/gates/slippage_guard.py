"""G19 — slippage and broker execution latency (news 57 / 59 / candle 50)."""

from __future__ import annotations

from nanobot.trading.gates.check import GateCheck, passed, veto
from nanobot.trading.gates.risk_snapshot import RiskSnapshot
from nanobot.trading.policy import live


def evaluate_slippage_guard(risk: RiskSnapshot | None) -> GateCheck:
    p = live()
    if risk is None:
        return passed()
    slip = risk.expected_slippage_points
    limit = min(p.SLIPPAGE_MAX_POINTS, p.SLIPPAGE_PROBE_POINTS)
    if slip is not None and slip > limit:
        return veto(
            "gate.slippage.expected",
            expected_slippage_points=slip,
            limit=limit,
        )
    latency = risk.exec_latency_ms
    if latency is not None and latency > p.EXEC_LATENCY_MAX_MS:
        return veto(
            "gate.slippage.latency",
            exec_latency_ms=latency,
            limit=p.EXEC_LATENCY_MAX_MS,
        )
    return passed()
