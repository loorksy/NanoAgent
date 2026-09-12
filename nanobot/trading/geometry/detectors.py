"""OHLC geometry helpers — swings, ATR, zones."""

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
    prev_high = next((s for s in reversed(swings) if s.type == "high"), None)
    prev_low = next((s for s in reversed(swings) if s.type == "low"), None)
    if prev_high and last.close > prev_high.price:
        events.append(
            StructureEvent(
                type="BOS",
                direction="bullish",
                broken_level=prev_high.price,
                break_candle_time=last.time_ms,
                confirmation_close=last.close,
                strength=0.7,
            )
        )
    if prev_low and last.close < prev_low.price:
        events.append(
            StructureEvent(
                type="BOS",
                direction="bearish",
                broken_level=prev_low.price,
                break_candle_time=last.time_ms,
                confirmation_close=last.close,
                strength=0.7,
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
