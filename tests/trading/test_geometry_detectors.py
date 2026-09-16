"""Deterministic S1 geometry detectors — FVG, CHoCH, Fibonacci, divergence."""

from nanobot.trading.geometry.detectors import (
    detect_divergence,
    detect_fair_value_gaps,
    detect_structure_events,
    fibonacci_retracement,
)
from nanobot.trading.geometry.snapshot import build_geometry_snapshot
from nanobot.trading.types import Candle, StructureResult, Swing


def _candle(time_ms: int, open_: float, high: float, low: float, close: float) -> Candle:
    return Candle(time_ms=time_ms, open=open_, high=high, low=low, close=close)


def test_bullish_fvg_three_candle_gap_and_fill():
    candles = [
        _candle(1, 9.0, 10.0, 8.0, 9.5),
        _candle(2, 10.0, 11.0, 9.8, 10.8),
        _candle(3, 12.2, 13.0, 12.0, 12.5),
        _candle(4, 12.4, 12.6, 11.5, 11.8),
    ]
    gaps = detect_fair_value_gaps(candles)
    assert gaps
    first = next(gap for gap in gaps if gap["low"] == 10.0 and gap["high"] == 12.0)
    assert first["side"] == "bullish"
    assert first["fill"] == "partial"


def test_choch_vs_bos_from_trend():
    swings = [
        Swing("low", 1, 90.0),
        Swing("high", 2, 100.0),
        Swing("low", 3, 92.0),
        Swing("high", 4, 110.0),
        Swing("low", 5, 100.0),
        Swing("high", 6, 120.0),
        Swing("low", 7, 112.0),
    ]
    choch_bar = _candle(8, 112.0, 113.0, 109.0, 110.0)
    events = detect_structure_events(swings, [_candle(i, 100, 100, 100, 100) for i in range(7)] + [choch_bar])
    assert any(event.type == "CHoCH" and event.direction == "bearish" for event in events)

    bos_bar = _candle(8, 120.0, 125.0, 119.0, 124.0)
    bos_events = detect_structure_events(swings, [_candle(i, 100, 100, 100, 100) for i in range(7)] + [bos_bar])
    assert any(event.type == "BOS" and event.direction == "bullish" for event in bos_events)


def test_fibonacci_last_impulse_618():
    swings = [Swing("low", 1, 100.0), Swing("high", 2, 200.0)]
    fib = fibonacci_retracement(swings)
    assert fib["impulse"] == "up"
    assert abs(float(fib["levels"]["0.618"]) - 138.2) < 0.01
    assert fib["equilibrium"] == 150.0


def test_rsi_bearish_divergence_on_higher_high():
    strong = [100.0 + i * 1.5 for i in range(16)]
    weak = [123.0, 122.6, 123.2, 122.8, 123.5, 123.1, 124.0]
    closes = strong + weak
    candles = [_candle(i, close, close + 0.3, close - 0.3, close) for i, close in enumerate(closes)]
    swings = [
        Swing("low", 2, closes[2]),
        Swing("low", 10, closes[10]),
        Swing("high", 15, closes[15]),
        Swing("high", 22, closes[22]),
    ]
    flags = detect_divergence(candles, swings)
    kinds = {flag["kind"] for flag in flags}
    assert "bearish_rsi" in kinds or "bearish_macd" in kinds


def test_geometry_snapshot_includes_s1_detectors():
    swings = [Swing("low", 1, 100.0), Swing("high", 2, 200.0)]
    structure = StructureResult("uptrend", swings, [], [], [])
    candles = [_candle(1, 100, 110, 90, 105), _candle(2, 130, 140, 129, 139), _candle(3, 150, 160, 149, 155)]
    snap = build_geometry_snapshot(structure, candles)
    assert "fvg" in snap
    assert snap["fibonacci"]["impulse"] == "up"
    assert snap["source"] == "deterministic_swings"
