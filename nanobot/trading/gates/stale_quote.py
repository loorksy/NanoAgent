"""G13 — stale quote, ping, and disconnect (playbook 189, section 6.6, news 10 / 71)."""

from __future__ import annotations

from nanobot.trading.gates.check import GateCheck, passed, unavailable, veto
from nanobot.trading.gates.risk_snapshot import RiskSnapshot
from nanobot.trading.policy import live


def evaluate_stale_quote(risk: RiskSnapshot | None) -> GateCheck:
    p = live()
    if risk is None or risk.quote_age_seconds is None:
        return unavailable("Quote age unavailable")
    age = float(risk.quote_age_seconds)
    if age > p.STALE_QUOTE_SECONDS:
        return veto(
            f"Last tick is {age:.1f}s old (limit {p.STALE_QUOTE_SECONDS:.0f}s)",
            quote_age_seconds=age,
            limit=p.STALE_QUOTE_SECONDS,
        )
    if age > p.DISCONNECT_ALERT_SECONDS:
        return veto(
            f"Price feed silent for {age:.1f}s (disconnect alert {p.DISCONNECT_ALERT_SECONDS:.0f}s)",
            quote_age_seconds=age,
            limit=p.DISCONNECT_ALERT_SECONDS,
        )
    if risk.ping_ms is not None and risk.ping_ms > p.PING_MAX_MS:
        return veto(
            f"Broker ping {risk.ping_ms:.0f}ms exceeds {p.PING_MAX_MS:.0f}ms",
            ping_ms=risk.ping_ms,
            limit=p.PING_MAX_MS,
        )
    return passed(quote_age_seconds=age)
