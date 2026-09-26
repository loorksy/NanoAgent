"""Replay the last 100–200 gold candles (T-5.2 / R1).

One deterministic strategy: ATR breakout with a 50% partial at 1R and a stop
moved to entry. Spread is charged on entry in gold points.
"""

from __future__ import annotations

from typing import Any

from nanobot.trading.geometry.detectors import compute_atr
from nanobot.trading.policy import GOLD_POINT
from nanobot.trading.types import Candle

MIN_BARS = 30
MAX_BARS = 200


def replay(
    candles: list[Candle],
    *,
    spread_points: float = 20.0,
    rr: float = 2.0,
    lookback: int = 5,
) -> dict[str, Any]:
    window = candles[-MAX_BARS:]
    if len(window) < MIN_BARS:
        return {
            "ok": False,
            "reason_key": "backtest.not_enough_bars",
            "candles": len(window),
            "trades": 0,
        }
    spread = spread_points * GOLD_POINT
    trades: list[dict[str, float]] = []
    start = max(lookback, 15)
    index = start
    while index < len(window) - 1:
        atr = compute_atr(window[: index + 1])
        if atr <= 0:
            index += 1
            continue
        bar = window[index]
        prior_high = max(item.high for item in window[index - lookback : index])
        prior_low = min(item.low for item in window[index - lookback : index])
        direction = ""
        if bar.close > prior_high:
            direction = "buy"
        elif bar.close < prior_low:
            direction = "sell"
        if not direction:
            index += 1
            continue
        entry = bar.close + spread if direction == "buy" else bar.close - spread
        risk = atr
        stop = entry - risk if direction == "buy" else entry + risk
        target = entry + rr * risk if direction == "buy" else entry - rr * risk
        partial_at = entry + risk if direction == "buy" else entry - risk
        pnl = 0.0
        closed_half = False
        exit_index = index
        for step in range(index + 1, len(window)):
            probe = window[step]
            exit_index = step
            if direction == "buy":
                if probe.low <= stop:
                    portion = 0.5 if closed_half else 1.0
                    pnl += (stop - entry) * portion
                    break
                if not closed_half and probe.high >= partial_at:
                    pnl += (partial_at - entry) * 0.5
                    closed_half = True
                    stop = entry
                if probe.high >= target:
                    portion = 0.5 if closed_half else 1.0
                    pnl += (target - entry) * portion
                    break
            else:
                if probe.high >= stop:
                    portion = 0.5 if closed_half else 1.0
                    pnl += (entry - stop) * portion
                    break
                if not closed_half and probe.low <= partial_at:
                    pnl += (entry - partial_at) * 0.5
                    closed_half = True
                    stop = entry
                if probe.low <= target:
                    portion = 0.5 if closed_half else 1.0
                    pnl += (entry - target) * portion
                    break
        else:
            last = window[-1].close
            portion = 0.5 if closed_half else 1.0
            pnl += ((last - entry) if direction == "buy" else (entry - last)) * portion
        r_multiple = pnl / risk if risk else 0.0
        trades.append({"pnl": pnl, "r": r_multiple})
        index = exit_index + 1
    from nanobot.trading.reports.scorecard import build_scorecard

    card = build_scorecard([{"pnl": row["pnl"], "r": row["r"]} for row in trades], period="replay")
    card["ok"] = True
    card["candles"] = len(window)
    card["strategy"] = "atr_breakout"
    return card
