"""Replay the last 100–200 gold candles (T-5.2 / R1).

One deterministic strategy: ATR breakout with a 50% partial at 1R and a stop
moved to entry. Spread is charged on entry in gold points.
"""

from __future__ import annotations

from typing import Any

from mokli.trading.geometry.detectors import compute_atr
from mokli.trading.policy import GOLD_POINT
from mokli.trading.types import Candle

MIN_BARS = 30
MAX_BARS = 200


def replay(
    candles: list[Candle],
    *,
    spread_points: float = 20.0,
    rr: float = 2.0,
    lookback: int = 5,
    rules: dict[str, Any] | None = None,
    confirm_candles: list[Candle] | None = None,
) -> dict[str, Any]:
    if rules:
        return _replay_rules(
            candles,
            rules,
            spread_points=spread_points,
            confirm_candles=confirm_candles,
        )
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
    from mokli.trading.reports.scorecard import build_scorecard

    card = build_scorecard([{"pnl": row["pnl"], "r": row["r"]} for row in trades], period="replay")
    card["ok"] = True
    card["candles"] = len(window)
    card["strategy"] = "atr_breakout"
    card["rs"] = [row["r"] for row in trades]
    return card


_HOUR_MS = 3_600_000
_CONFIRM_BAR_MS = 4 * _HOUR_MS


def _account_pnls(trades: list[dict[str, float]], risk_percent: object) -> list[dict[str, float]]:
    """Size each trade as a fraction of current equity.

    A full stop at 1% changes equity by -0.01. The R multiple stays the
    price result divided by the stop distance. Missing risk leaves the
    price result unchanged.
    """
    if isinstance(risk_percent, bool) or not isinstance(risk_percent, (int, float)):
        return trades
    fraction = float(risk_percent) / 100.0
    if fraction <= 0:
        return trades
    equity = 1.0
    sized: list[dict[str, float]] = []
    for row in trades:
        change = float(row["r"]) * equity * fraction
        sized.append({"pnl": change, "r": float(row["r"])})
        equity += change
    return sized


def _higher_timeframe_rising(confirm: list[Candle], at_ms: int, *, bars: int) -> bool:
    """The latest closed higher-timeframe close is above the close ``bars`` earlier.

    ``at_ms`` is the entry bar's open. That close is known one hour later. A
    four-hour bar is known four hours after its open, so a bar that is still
    forming cannot confirm or block the trend. One green bar after a decline
    is not a trend. ``bars`` is the spec's confirmation span.
    """
    known_at = at_ms + _HOUR_MS
    prior = [bar for bar in confirm if bar.time_ms + _CONFIRM_BAR_MS <= known_at]
    span = max(1, bars)
    if len(prior) <= span:
        return False
    return prior[-1].close > prior[-1 - span].close


def _replay_rules(
    candles: list[Candle],
    rules: dict[str, Any],
    *,
    spread_points: float,
    confirm_candles: list[Candle] | None = None,
) -> dict[str, Any]:
    """Interpret a checked spec. Long break of the previous bar, stop under the swing low."""
    window = candles[-MAX_BARS:]
    if len(window) < MIN_BARS:
        return {
            "ok": False,
            "reason_key": "backtest.not_enough_bars",
            "candles": len(window),
            "trades": 0,
            "strategy": str(rules.get("name") or "spec"),
        }
    if rules.get("entry") != "break_prior_high":
        return {
            "ok": False,
            "reason_key": "strategy.unsupported_entry",
            "candles": len(window),
            "trades": 0,
            "strategy": str(rules.get("name") or "spec"),
        }
    lookback = int(rules.get("lookback") or 5)
    entry_lookback = int(rules.get("entry_lookback") or 1)
    confirm_bars = int(rules.get("confirm_bars") or 4)
    rr = float(rules.get("target_rr") or 2.0)
    spread = spread_points * GOLD_POINT
    buffer = GOLD_POINT
    trades: list[dict[str, float]] = []
    start = max(lookback, entry_lookback, confirm_bars, 15)
    index = start
    while index < len(window) - 1:
        bar = window[index]
        entry_prior = window[index - entry_lookback : index]
        swing = window[index - lookback : index]
        prior_high = max(item.high for item in entry_prior)
        swing_low = min(item.low for item in swing)
        if bar.close <= prior_high:
            index += 1
            continue
        if confirm_candles is not None:
            if not _higher_timeframe_rising(
                confirm_candles,
                bar.time_ms,
                bars=confirm_bars,
            ):
                index += 1
                continue
        else:
            earlier = window[index - confirm_bars].close
            if bar.close <= earlier:
                index += 1
                continue
        entry = bar.close + spread
        stop = swing_low - buffer
        risk = entry - stop
        if risk <= 0:
            index += 1
            continue
        target = entry + rr * risk
        pnl = 0.0
        exit_index = index
        for step in range(index + 1, len(window)):
            probe = window[step]
            exit_index = step
            if probe.low <= stop:
                pnl += stop - entry
                break
            if probe.high >= target:
                pnl += target - entry
                break
        else:
            pnl += window[-1].close - entry
        trades.append({"pnl": pnl, "r": pnl / risk})
        index = exit_index + 1
    from mokli.trading.reports.scorecard import build_scorecard

    rs = [row["r"] for row in trades]
    sized = _account_pnls(trades, rules.get("risk_percent"))
    card = build_scorecard([{"pnl": row["pnl"], "r": row["r"]} for row in sized], period="replay")
    card["ok"] = True
    card["candles"] = len(window)
    card["strategy"] = str(rules.get("name") or "spec")
    card["rs"] = rs
    card["risk_percent"] = rules.get("risk_percent")
    card["entry_lookback"] = entry_lookback
    card["lookback"] = lookback
    card["confirm_bars"] = confirm_bars
    card["target_rr"] = rr
    if confirm_candles is not None:
        card["confirm_timeframe"] = "4h"
    return card
