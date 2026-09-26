"""Closed-trade scorecard (T-6.4)."""

from __future__ import annotations

from typing import Any


def _num(row: dict[str, Any], key: str) -> float:
    raw = row.get(key)
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return float(raw)
    return 0.0


def build_scorecard(trades: list[dict[str, Any]], *, period: str = "week") -> dict[str, Any]:
    pnls = [_num(row, "pnl") for row in trades]
    rs = [_num(row, "r") for row in trades]
    wins = sum(1 for value in pnls if value > 0)
    count = len(trades)
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for value in pnls:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    return {
        "kind": "scorecard",
        "period": period,
        "trades": count,
        "win_rate": (wins / count) if count else 0.0,
        "expectancy": (sum(pnls) / count) if count else 0.0,
        "avg_r": (sum(rs) / count) if count else 0.0,
        "pnl": sum(pnls),
        "max_dd": max_dd,
    }
