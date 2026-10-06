"""G13 — stale quote, ping, and disconnect (playbook 189, section 6.6, news 10 / 71)."""

from __future__ import annotations

import time
from datetime import UTC, datetime

from mokli.trading.gates.check import GateCheck, passed, unavailable, veto
from mokli.trading.gates.risk_snapshot import RiskSnapshot
from mokli.trading.policy import live


def evaluate_stale_quote(risk: RiskSnapshot | None) -> GateCheck:
    p = live()
    if risk is None or risk.quote_age_seconds is None:
        return unavailable("gate.quote.age_unavailable")
    age = float(risk.quote_age_seconds)
    if age > p.STALE_QUOTE_SECONDS:
        return veto(
            "gate.quote.stale",
            quote_age_seconds=age,
            limit=p.STALE_QUOTE_SECONDS,
        )
    if age > p.DISCONNECT_ALERT_SECONDS:
        return veto(
            "gate.quote.disconnect",
            quote_age_seconds=age,
            limit=p.DISCONNECT_ALERT_SECONDS,
        )
    if risk.ping_ms is not None and risk.ping_ms > p.PING_MAX_MS:
        return veto(
            "gate.quote.ping",
            ping_ms=risk.ping_ms,
            limit=p.PING_MAX_MS,
        )
    return passed(quote_age_seconds=age)


def broker_quote_age_seconds(raw: object, *, now: float | None = None) -> float | None:
    """Age of a broker timestamp. ``None`` when the broker sent no clock."""
    if isinstance(raw, bool) or raw is None:
        return None
    if isinstance(raw, (int, float)):
        stamp = float(raw)
        if stamp > 10_000_000_000:
            stamp /= 1000.0
        if stamp <= 0:
            return None
        return max(0.0, (time.time() if now is None else now) - stamp)
    if not isinstance(raw, str) or not raw.strip():
        return None
    text = raw.strip().replace("Z", "+00:00")
    if "." in text:
        left, right = text.split(".", 1)
        digits: list[str] = []
        rest = ""
        for index, char in enumerate(right):
            if char.isdigit() and len(digits) < 6:
                digits.append(char)
                continue
            rest = right[index:]
            break
        text = f"{left}.{''.join(digits)}{rest}" if digits else f"{left}{rest}"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return max(0.0, (time.time() if now is None else now) - parsed.timestamp())
