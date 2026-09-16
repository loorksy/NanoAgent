"""G19 — slippage and broker execution latency (news 57 / 59)."""

from __future__ import annotations

from nanobot.trading.gates.check import GateCheck, passed, veto
from nanobot.trading.gates.risk_snapshot import RiskSnapshot
from nanobot.trading.policy import live


def evaluate_slippage_guard(risk: RiskSnapshot | None) -> GateCheck:
    p = live()
    if risk is None:
        return passed()
    slip = risk.expected_slippage_points
    if slip is not None and slip > p.SLIPPAGE_MAX_POINTS:
        return veto(
            f"Expected slippage {slip:.1f} points exceeds {p.SLIPPAGE_MAX_POINTS:.0f}",
            expected_slippage_points=slip,
            limit=p.SLIPPAGE_MAX_POINTS,
        )
    latency = risk.exec_latency_ms
    if latency is not None and latency > p.EXEC_LATENCY_MAX_MS:
        return veto(
            f"Broker execution latency {latency:.0f}ms exceeds {p.EXEC_LATENCY_MAX_MS:.0f}ms",
            exec_latency_ms=latency,
            limit=p.EXEC_LATENCY_MAX_MS,
        )
    return passed()
