"""News-candle detector — deterministic ATR / range / spread fingerprints.

Candle encyclopedia 16, 17, 18, 100 and playbook 186.
"""

from __future__ import annotations

from nanobot.trading.gates.check import GateCheck, passed, veto
from nanobot.trading.policy import GOLD_POINT, live


def is_news_candle(
    *,
    candle_range: float,
    atr: float,
    m1_range: float | None = None,
    m5_range: float | None = None,
    adr: float | None = None,
    spread_points: float | None = None,
    normal_spread_points: float | None = None,
    tick_volume_z: float | None = None,
) -> bool:
    p = live()
    if atr > 0 and candle_range >= p.NEWS_CANDLE_ATR_MULT * atr:
        return True
    if m1_range is not None and m1_range / GOLD_POINT >= p.NEWS_CANDLE_M1_POINTS:
        return True
    if m5_range is not None and adr and adr > 0 and m5_range >= p.NEWS_CANDLE_M5_ADR_FRACTION * adr:
        return True
    spread_blow = (
        spread_points is not None
        and normal_spread_points
        and normal_spread_points > 0
        and spread_points >= normal_spread_points * p.SPREAD_MULTIPLIER_PRE_NEWS
    )
    atr_blow = atr > 0 and candle_range >= p.NEWS_CANDLE_ATR_MULT * atr
    vol_blow = tick_volume_z is not None and tick_volume_z > p.NEWS_CANDLE_VOLUME_Z
    return bool(atr_blow and spread_blow and vol_blow)


def evaluate_news_candle_shield(
    *,
    candle_range: float,
    atr: float,
    m1_range: float | None = None,
    m5_range: float | None = None,
    adr: float | None = None,
    spread_points: float | None = None,
    normal_spread_points: float | None = None,
    tick_volume_z: float | None = None,
    points_last_minute: float | None = None,
) -> GateCheck:
    p = live()
    detected = is_news_candle(
        candle_range=candle_range,
        atr=atr,
        m1_range=m1_range,
        m5_range=m5_range,
        adr=adr,
        spread_points=spread_points,
        normal_spread_points=normal_spread_points,
        tick_volume_z=tick_volume_z,
    )
    if points_last_minute is not None and points_last_minute >= p.EMERGENCY_MOVE_POINTS_PER_MINUTE:
        return veto(
            "gate.news_candle.burst",
            points_last_minute=points_last_minute,
            news_candle=detected,
        )
    if detected:
        return veto(
            "gate.news_candle.fingerprint",
            candle_range=candle_range,
            atr=atr,
        )
    return passed(news_candle=False)
