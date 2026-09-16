"""OHLC geometry helpers — swings, ATR, zones, FVG, Fibonacci, divergence."""

from __future__ import annotations

from nanobot.trading.types import (
    Candle,
    LiquiditySweep,
    PriceLevel,
    StructureEvent,
    SupplyDemandZone,
    Swing,
    TrendLabel,
)


def compute_atr(candles: list[Candle], period: int = 14) -> float:
    if len(candles) < 2:
        return 0.0
    trs: list[float] = []
    for i in range(1, len(candles)):
        c = candles[i]
        prev = candles[i - 1]
        tr = max(c.high - c.low, abs(c.high - prev.close), abs(c.low - prev.close))
        trs.append(tr)
    window = trs[-period:] if len(trs) >= period else trs
    return sum(window) / len(window) if window else 0.0


def find_swings(candles: list[Candle], left: int = 2, right: int = 2) -> list[Swing]:
    swings: list[Swing] = []
    for i in range(left, len(candles) - right):
        hi = candles[i].high
        lo = candles[i].low
        if all(hi >= candles[j].high for j in range(i - left, i + right + 1) if j != i):
            swings.append(Swing(type="high", time=candles[i].time_ms, price=hi))
        if all(lo <= candles[j].low for j in range(i - left, i + right + 1) if j != i):
            swings.append(Swing(type="low", time=candles[i].time_ms, price=lo))
    return swings


def infer_trend(swings: list[Swing]) -> TrendLabel:
    highs = [s for s in swings if s.type == "high"][-3:]
    lows = [s for s in swings if s.type == "low"][-3:]
    if len(highs) < 2 or len(lows) < 2:
        return "unknown"
    hh = highs[-1].price > highs[-2].price
    hl = lows[-1].price > lows[-2].price
    lh = highs[-1].price < highs[-2].price
    ll = lows[-1].price < lows[-2].price
    if hh and hl:
        return "uptrend"
    if lh and ll:
        return "downtrend"
    return "range"


def support_resistance(swings: list[Swing], last_close: float) -> tuple[list[PriceLevel], list[PriceLevel]]:
    support = [PriceLevel(price=s.price, time=s.time) for s in swings if s.type == "low" and s.price < last_close]
    resistance = [PriceLevel(price=s.price, time=s.time) for s in swings if s.type == "high" and s.price > last_close]
    support.sort(key=lambda x: abs(x.price - last_close))
    resistance.sort(key=lambda x: abs(x.price - last_close))
    return support[:5], resistance[:5]


def detect_structure_events(swings: list[Swing], candles: list[Candle]) -> list[StructureEvent]:
    events: list[StructureEvent] = []
    if len(swings) < 3 or not candles:
        return events
    last = candles[-1]
    trend = infer_trend(swings)
    prev_high = next((s for s in reversed(swings) if s.type == "high"), None)
    prev_low = next((s for s in reversed(swings) if s.type == "low"), None)
    if prev_high and last.close > prev_high.price:
        choch = trend == "downtrend"
        events.append(
            StructureEvent(
                type="CHoCH" if choch else "BOS",
                direction="bullish",
                broken_level=prev_high.price,
                break_candle_time=last.time_ms,
                confirmation_close=last.close,
                strength=0.8 if choch else 0.7,
            )
        )
    if prev_low and last.close < prev_low.price:
        choch = trend == "uptrend"
        events.append(
            StructureEvent(
                type="CHoCH" if choch else "BOS",
                direction="bearish",
                broken_level=prev_low.price,
                break_candle_time=last.time_ms,
                confirmation_close=last.close,
                strength=0.8 if choch else 0.7,
            )
        )
    return events


def find_equal_levels(swings: list[Swing], tolerance_pct: float = 0.0008) -> tuple[list[PriceLevel], list[PriceLevel]]:
    highs = [s for s in swings if s.type == "high"]
    lows = [s for s in swings if s.type == "low"]
    eq_highs: list[PriceLevel] = []
    eq_lows: list[PriceLevel] = []
    for i, a in enumerate(highs):
        for b in highs[i + 1 :]:
            if abs(a.price - b.price) / max(a.price, 1) <= tolerance_pct:
                eq_highs.append(PriceLevel(price=(a.price + b.price) / 2, time=b.time))
    for i, a in enumerate(lows):
        for b in lows[i + 1 :]:
            if abs(a.price - b.price) / max(a.price, 1) <= tolerance_pct:
                eq_lows.append(PriceLevel(price=(a.price + b.price) / 2, time=b.time))
    return eq_highs[:5], eq_lows[:5]


def detect_sweeps(candles: list[Candle], eq_highs: list[PriceLevel], eq_lows: list[PriceLevel]) -> list[LiquiditySweep]:
    sweeps: list[LiquiditySweep] = []
    if not candles:
        return sweeps
    last = candles[-1]
    for level in eq_highs:
        if last.high > level.price and last.close < level.price:
            sweeps.append(
                LiquiditySweep(
                    side="buy_side",
                    swept_level=level.price,
                    candle_time=last.time_ms,
                    wick_extreme=last.high,
                    close_back_inside=True,
                    strength=0.75,
                )
            )
    for level in eq_lows:
        if last.low < level.price and last.close > level.price:
            sweeps.append(
                LiquiditySweep(
                    side="sell_side",
                    swept_level=level.price,
                    candle_time=last.time_ms,
                    wick_extreme=last.low,
                    close_back_inside=True,
                    strength=0.75,
                )
            )
    return sweeps


def build_supply_demand_zones(candles: list[Candle], atr: float) -> list[SupplyDemandZone]:
    zones: list[SupplyDemandZone] = []
    if len(candles) < 10 or atr <= 0:
        return zones
    body = candles[-1].close - candles[-1].open
    impulse = abs(body) > atr * 0.6
    if impulse and body > 0:
        base = candles[-2]
        zones.append(
            SupplyDemandZone(
                type="demand",
                low=min(base.low, base.close),
                high=max(base.open, base.close),
                time=base.time_ms,
            )
        )
    elif impulse:
        base = candles[-2]
        zones.append(
            SupplyDemandZone(
                type="supply",
                low=min(base.open, base.close),
                high=max(base.high, base.close),
                time=base.time_ms,
            )
        )
    return zones


_FIB_RATIOS = (0.0, 0.5, 0.618, 0.786, 1.0)
_FIB_EXTENSIONS = (1.272, 1.618)


def _gap_fill(
    later: list[Candle],
    gap_low: float,
    gap_high: float,
    side: str,
) -> str:
    fill = "open"
    for candle in later:
        if side == "bullish":
            if candle.low <= gap_low:
                return "full"
            if candle.low < gap_high:
                fill = "partial"
        else:
            if candle.high >= gap_high:
                return "full"
            if candle.high > gap_low:
                fill = "partial"
    return fill


def detect_fair_value_gaps(candles: list[Candle], limit: int = 8) -> list[dict[str, float | str | int]]:
    """Three-candle imbalance (S1.1). Bullish: left.high < right.low. Bearish: left.low > right.high."""
    gaps: list[dict[str, float | str | int]] = []
    if len(candles) < 3:
        return gaps
    for i in range(2, len(candles)):
        left, right = candles[i - 2], candles[i]
        if left.high < right.low:
            low, high = left.high, right.low
            side = "bullish"
        elif left.low > right.high:
            low, high = right.high, left.low
            side = "bearish"
        else:
            continue
        gaps.append(
            {
                "side": side,
                "low": low,
                "high": high,
                "time": right.time_ms,
                "fill": _gap_fill(candles[i + 1 :], low, high, side),
            }
        )
    return gaps[-limit:]


def fibonacci_retracement(swings: list[Swing]) -> dict[str, object]:
    """Last impulse discount/premium map (S1.5)."""
    last_high = next((s for s in reversed(swings) if s.type == "high"), None)
    last_low = next((s for s in reversed(swings) if s.type == "low"), None)
    if last_high is None or last_low is None:
        return {}
    impulse_up = last_high.time >= last_low.time
    start = last_low.price if impulse_up else last_high.price
    end = last_high.price if impulse_up else last_low.price
    span = end - start
    if abs(span) < 1e-9:
        return {}
    levels = {f"{ratio:g}": round(end - span * ratio, 5) for ratio in _FIB_RATIOS}
    extensions = {f"{ratio:g}": round(start + span * ratio, 5) for ratio in _FIB_EXTENSIONS}
    equilibrium = (start + end) / 2
    return {
        "impulse": "up" if impulse_up else "down",
        "start": start,
        "end": end,
        "equilibrium": equilibrium,
        "discount_below": equilibrium if impulse_up else None,
        "premium_above": equilibrium if impulse_up else None,
        "levels": levels,
        "extensions": extensions,
    }


def compute_rsi(closes: list[float], period: int = 14) -> list[float]:
    if len(closes) < 2:
        return [50.0] * len(closes)
    rsi = [50.0]
    gains = 0.0
    losses = 0.0
    avg_gain = 0.0
    avg_loss = 0.0
    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gain = max(change, 0.0)
        loss = max(-change, 0.0)
        if i <= period:
            gains += gain
            losses += loss
            if i < period:
                rsi.append(50.0)
                continue
            avg_gain = gains / period
            avg_loss = losses / period
        else:
            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period
        if avg_loss == 0:
            rsi.append(100.0)
        else:
            relative = avg_gain / avg_loss
            rsi.append(100.0 - (100.0 / (1.0 + relative)))
    return rsi


def _ema(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    k = 2.0 / (period + 1)
    out = [values[0]]
    for value in values[1:]:
        out.append(value * k + out[-1] * (1.0 - k))
    return out


def compute_macd(closes: list[float]) -> tuple[list[float], list[float]]:
    if len(closes) < 26:
        zeros = [0.0] * len(closes)
        return zeros, zeros
    macd_line = [a - b for a, b in zip(_ema(closes, 12), _ema(closes, 26), strict=True)]
    signal = _ema(macd_line, 9)
    return macd_line, signal


def _nearest_index(times: dict[int, int], stamp: int) -> int | None:
    if not times:
        return None
    nearest = min(times, key=lambda key: abs(key - stamp))
    return times[nearest]


def detect_divergence(candles: list[Candle], swings: list[Swing]) -> list[dict[str, str | float]]:
    """RSI / MACD swing divergence (S1.7). Warning only — not a market order."""
    flags: list[dict[str, str | float]] = []
    if len(candles) < 20 or len(swings) < 4:
        return flags
    closes = [c.close for c in candles]
    rsis = compute_rsi(closes)
    macd_line, _signal = compute_macd(closes)
    times = {c.time_ms: i for i, c in enumerate(candles)}
    highs = [s for s in swings if s.type == "high"][-2:]
    lows = [s for s in swings if s.type == "low"][-2:]
    if len(highs) == 2:
        i0 = _nearest_index(times, highs[0].time)
        i1 = _nearest_index(times, highs[1].time)
        if i0 is not None and i1 is not None and highs[1].price > highs[0].price:
            if rsis[i1] < rsis[i0]:
                flags.append({"kind": "bearish_rsi", "price": highs[1].price, "oscillator": rsis[i1]})
            if macd_line[i1] < macd_line[i0]:
                flags.append({"kind": "bearish_macd", "price": highs[1].price, "oscillator": macd_line[i1]})
    if len(lows) == 2:
        i0 = _nearest_index(times, lows[0].time)
        i1 = _nearest_index(times, lows[1].time)
        if i0 is not None and i1 is not None and lows[1].price < lows[0].price:
            if rsis[i1] > rsis[i0]:
                flags.append({"kind": "bullish_rsi", "price": lows[1].price, "oscillator": rsis[i1]})
            if macd_line[i1] > macd_line[i0]:
                flags.append({"kind": "bullish_macd", "price": lows[1].price, "oscillator": macd_line[i1]})
    return flags
