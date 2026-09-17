"""G10 — cooldown lock after consecutive losses (3.4, playbook 187, news 62)."""

from __future__ import annotations

from nanobot.trading.gates.check import GateCheck, passed, veto
from nanobot.trading.gates.risk_snapshot import RiskSnapshot


def evaluate_cooldown_lock(risk: RiskSnapshot | None, *, now_ms: int) -> GateCheck:
    if risk is None:
        return passed(cooldown=False)
    until = int(risk.cooldown_until_ms or 0)
    if until > now_ms:
        remaining = max(0, int((until - now_ms) / 60000))
        return veto(
            "gate.cooldown.active",
            remaining_minutes=remaining,
            cooldown_reason=risk.cooldown_reason,
        )
    return passed(cooldown=False)
