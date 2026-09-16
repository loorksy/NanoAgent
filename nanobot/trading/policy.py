"""Deterministic numeric policy for gold risk, news, and execution gates.

Every constant is tagged with the spec source that owns it. Interpreters must
not re-state these numbers as model-memorized rules — the gates enforce them.

Module-level names remain the documented defaults. Runtime evaluation reads
``live()``, which loads ``Config.trading_risk_parameters`` from disk so WebUI
edits apply without redeploying code.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Gold quoting: $1.00 move = 100 points (playbook 134).
GOLD_POINT = 0.01
USD_PER_POINT_PER_LOT = 1.0  # standard XAUUSD contract scaling

# ---------------------------------------------------------------------------
# Section 3 — Risk guardrails
# ---------------------------------------------------------------------------
RISK_PCT_DEFAULT = 0.01  # 3.1 / playbook 47 — 1% of balance
RISK_PCT_MAX = 0.02  # 3.1 / playbook 47 — never size above 2%
RISK_PCT_NEWS_DAY = 0.005  # news 16 — half risk on high-impact data days
DAILY_DRAWDOWN_PCT = 0.03  # 3.2 / playbook 191
EQUITY_SPIKE_PCT = 0.02  # news 61 — 2% floating equity drop in one candle
SPREAD_MAX_POINTS = 60.0  # 3.3 / news 56 — 60 gold points
SPREAD_STABLE_SECONDS = 180.0  # news 56 — 3 minutes of stable spread
SPREAD_MULTIPLIER_PRE_NEWS = 3.0  # news 5 — 3x normal two minutes before news
SPREAD_PRE_NEWS_MINUTES = 2.0  # news 5
COOLDOWN_CONSECUTIVE_LOSSES = 2  # 3.4
COOLDOWN_AFTER_TWO_LOSSES_MINUTES = 180  # 3.4 midpoint of 2–4 hours
COOLDOWN_AFTER_TWO_LOSSES_SESSION_MINUTES = 60  # playbook 187
COOLDOWN_AFTER_NEWS_STOP_MINUTES = 45  # news 62
MAX_OPEN_GOLD_POSITIONS = 2  # 3.5
MIN_RR = 2.0  # 3.6 — farthest target must be at least 1:2
MIN_RR_LIVE_FILL = 1.5  # playbook 196 — cancel if live fill degrades below 1:1.5

# ---------------------------------------------------------------------------
# Section 4 / playbook time stops and management
# ---------------------------------------------------------------------------
IDEA_STALE_HOURS = 4.0  # playbook 12
PENDING_TTL_HOURS = 3.0  # playbook 183 (stricter than 12)
TIME_STOP_HOURS = 3.0  # playbook 36
HALF_DISTANCE_FRACTION = 0.50  # playbook 193 / news 65
NEWS_SHIELD_MINUTES = 10.0  # 4.5 / news 2–3
FLAT_NEAR_ENTRY_POINTS = 30.0  # news 4
PARTIAL_TP1_FRACTION = 0.50  # 4.4 / playbook 137
PARTIAL_TP2_FRACTION = 0.25  # 4.4
PARTIAL_TP_SPLIT = (0.40, 0.30, 0.30)  # playbook 153
BREAKEVEN_RR = 1.0  # 4.3 / playbook 38
PROFIT_LOCK_AT_TARGET_FRACTION = 0.70  # playbook 39
PROFIT_LOCK_KEEP_FRACTION = 0.50  # playbook 39
OVERNIGHT_SL_BUFFER_POINTS = 20.0  # playbook 52
POST_NEWS_SL_BUFFER_POINTS = 30.0  # news 63
TRAIL_ATR_MULT = 1.5  # 4.2 / playbook 29

# ---------------------------------------------------------------------------
# Quote / connection / execution quality
# ---------------------------------------------------------------------------
STALE_QUOTE_SECONDS = 5.0  # playbook 189
DISCONNECT_ALERT_SECONDS = 10.0  # 6.6 / news 71
PING_MAX_MS = 50.0  # news 10
EXEC_LATENCY_MAX_MS = 1000.0  # news 59
SLIPPAGE_MAX_POINTS = 25.0  # news 57
SLIPPAGE_PROBE_POINTS = 20.0  # candle-enc 50
BAD_TICK_POINTS = 80.0  # 7.4 / news 66
MARGIN_MIN_PCT = 500.0  # news 70
PROPOSAL_TTL_SECONDS = 120.0  # HITL bracket expiry (execution, not rule 182)
MAX_CONFIRM_SLIPPAGE_POINTS = 25.0  # same as news 57, enforced on confirm

# ---------------------------------------------------------------------------
# Session / calendar locks
# ---------------------------------------------------------------------------
MIDNIGHT_SPREAD_START_HM = (23, 55)  # playbook 118
MIDNIGHT_SPREAD_END_HM = (0, 15)  # playbook 118
DAILY_CLOSE_LOCK_MINUTES = 15  # playbook 195
DAILY_CLOSE_HOUR_UTC = 21
ROLLOVER_MINUTE_START = 58  # news 64
ROLLOVER_MINUTE_END = 2  # news 64 (wraps hour)
ROLLOVER_NEWS_MINUTES = 60.0
POST_NEWS_ENTRY_WAIT_MINUTES = 15.0  # news 73 / existing G1 after-window
PRE_NEWS_FREEZE_MINUTES = 15.0  # news 1 (G1 already uses 30m — stricter)
NEWS_BLACKOUT_BEFORE_MINUTES = 30.0  # G1
NEWS_BLACKOUT_AFTER_MINUTES = 15.0  # G1
NEWS_VOID_SECONDS = 60.0  # news 35
FIRST_MINUTE_DEAD = 60.0  # news 35

# ---------------------------------------------------------------------------
# Volatility / ADR / gap
# ---------------------------------------------------------------------------
ADR_CHASE_PCT = 2.0  # news 82 — 200% of ADR, no chase
GAP_NO_CHASE_POINTS = 150.0  # news 90
NEWS_CANDLE_ATR_MULT = 3.0  # candle-enc 16 / 100
NEWS_CANDLE_M1_POINTS = 60.0  # candle-enc 17
NEWS_CANDLE_M5_ADR_FRACTION = 0.40  # candle-enc 18
NEWS_CANDLE_VOLUME_Z = 3.5
ATR_DOUBLE_LOT_HALVE = 2.0  # news 67
EMERGENCY_MOVE_POINTS_PER_MINUTE = 80.0  # playbook 186
MAX_REPRICE_ROUNDS = 2  # G7
LIQUIDITY_PROXIMITY_ATR = 0.3  # G2
ENTRY_MAX_ATR_DISTANCE = 0.3  # G6
TARGET_MAX_ATR_DISTANCE = 25.0  # G6
G7_MAX_SLIPPAGE_ATR = 0.5  # G7
LOT_DUAL_CHECK_HIGH = 2.0  # playbook 188
LOT_DUAL_CHECK_LOW = 0.5  # playbook 188

# Magic numbers (playbook 185) — identifiers, not operator thresholds
MAGIC_SCALP = 18501
MAGIC_SWING = 18502


@dataclass(frozen=True)
class LiveRiskPolicy:
    """Gate-unit snapshot of the currently loaded risk parameters."""

    RISK_PCT_DEFAULT: float
    RISK_PCT_MAX: float
    RISK_PCT_NEWS_DAY: float
    DAILY_DRAWDOWN_PCT: float
    EQUITY_SPIKE_PCT: float
    SPREAD_MAX_POINTS: float
    SPREAD_STABLE_SECONDS: float
    SPREAD_MULTIPLIER_PRE_NEWS: float
    SPREAD_PRE_NEWS_MINUTES: float
    COOLDOWN_CONSECUTIVE_LOSSES: int
    COOLDOWN_AFTER_TWO_LOSSES_MINUTES: float
    COOLDOWN_AFTER_TWO_LOSSES_SESSION_MINUTES: float
    COOLDOWN_AFTER_NEWS_STOP_MINUTES: float
    MAX_OPEN_GOLD_POSITIONS: int
    MIN_RR: float
    MIN_RR_LIVE_FILL: float
    IDEA_STALE_HOURS: float
    PENDING_TTL_HOURS: float
    TIME_STOP_HOURS: float
    HALF_DISTANCE_FRACTION: float
    NEWS_SHIELD_MINUTES: float
    FLAT_NEAR_ENTRY_POINTS: float
    PARTIAL_TP1_FRACTION: float
    PARTIAL_TP2_FRACTION: float
    PARTIAL_TP_SPLIT: tuple[float, float, float]
    BREAKEVEN_RR: float
    PROFIT_LOCK_AT_TARGET_FRACTION: float
    PROFIT_LOCK_KEEP_FRACTION: float
    OVERNIGHT_SL_BUFFER_POINTS: float
    POST_NEWS_SL_BUFFER_POINTS: float
    TRAIL_ATR_MULT: float
    STALE_QUOTE_SECONDS: float
    DISCONNECT_ALERT_SECONDS: float
    PING_MAX_MS: float
    EXEC_LATENCY_MAX_MS: float
    SLIPPAGE_MAX_POINTS: float
    SLIPPAGE_PROBE_POINTS: float
    BAD_TICK_POINTS: float
    MARGIN_MIN_PCT: float
    PROPOSAL_TTL_SECONDS: float
    MAX_CONFIRM_SLIPPAGE_POINTS: float
    MIDNIGHT_SPREAD_START_HM: tuple[int, int]
    MIDNIGHT_SPREAD_END_HM: tuple[int, int]
    DAILY_CLOSE_LOCK_MINUTES: float
    DAILY_CLOSE_HOUR_UTC: int
    ROLLOVER_MINUTE_START: int
    ROLLOVER_MINUTE_END: int
    ROLLOVER_NEWS_MINUTES: float
    POST_NEWS_ENTRY_WAIT_MINUTES: float
    PRE_NEWS_FREEZE_MINUTES: float
    NEWS_BLACKOUT_BEFORE_MINUTES: float
    NEWS_BLACKOUT_AFTER_MINUTES: float
    NEWS_VOID_SECONDS: float
    FIRST_MINUTE_DEAD: float
    ADR_CHASE_PCT: float
    GAP_NO_CHASE_POINTS: float
    NEWS_CANDLE_ATR_MULT: float
    NEWS_CANDLE_M1_POINTS: float
    NEWS_CANDLE_M5_ADR_FRACTION: float
    NEWS_CANDLE_VOLUME_Z: float
    ATR_DOUBLE_LOT_HALVE: float
    EMERGENCY_MOVE_POINTS_PER_MINUTE: float
    MAX_REPRICE_ROUNDS: int
    LIQUIDITY_PROXIMITY_ATR: float
    ENTRY_MAX_ATR_DISTANCE: float
    TARGET_MAX_ATR_DISTANCE: float
    G7_MAX_SLIPPAGE_ATR: float
    LOT_DUAL_CHECK_HIGH: float
    LOT_DUAL_CHECK_LOW: float
    GOLD_POINT: float = GOLD_POINT
    USD_PER_POINT_PER_LOT: float = USD_PER_POINT_PER_LOT


def _defaults() -> LiveRiskPolicy:
    return LiveRiskPolicy(
        RISK_PCT_DEFAULT=RISK_PCT_DEFAULT,
        RISK_PCT_MAX=RISK_PCT_MAX,
        RISK_PCT_NEWS_DAY=RISK_PCT_NEWS_DAY,
        DAILY_DRAWDOWN_PCT=DAILY_DRAWDOWN_PCT,
        EQUITY_SPIKE_PCT=EQUITY_SPIKE_PCT,
        SPREAD_MAX_POINTS=SPREAD_MAX_POINTS,
        SPREAD_STABLE_SECONDS=SPREAD_STABLE_SECONDS,
        SPREAD_MULTIPLIER_PRE_NEWS=SPREAD_MULTIPLIER_PRE_NEWS,
        SPREAD_PRE_NEWS_MINUTES=SPREAD_PRE_NEWS_MINUTES,
        COOLDOWN_CONSECUTIVE_LOSSES=COOLDOWN_CONSECUTIVE_LOSSES,
        COOLDOWN_AFTER_TWO_LOSSES_MINUTES=float(COOLDOWN_AFTER_TWO_LOSSES_MINUTES),
        COOLDOWN_AFTER_TWO_LOSSES_SESSION_MINUTES=float(
            COOLDOWN_AFTER_TWO_LOSSES_SESSION_MINUTES
        ),
        COOLDOWN_AFTER_NEWS_STOP_MINUTES=float(COOLDOWN_AFTER_NEWS_STOP_MINUTES),
        MAX_OPEN_GOLD_POSITIONS=MAX_OPEN_GOLD_POSITIONS,
        MIN_RR=MIN_RR,
        MIN_RR_LIVE_FILL=MIN_RR_LIVE_FILL,
        IDEA_STALE_HOURS=IDEA_STALE_HOURS,
        PENDING_TTL_HOURS=PENDING_TTL_HOURS,
        TIME_STOP_HOURS=TIME_STOP_HOURS,
        HALF_DISTANCE_FRACTION=HALF_DISTANCE_FRACTION,
        NEWS_SHIELD_MINUTES=NEWS_SHIELD_MINUTES,
        FLAT_NEAR_ENTRY_POINTS=FLAT_NEAR_ENTRY_POINTS,
        PARTIAL_TP1_FRACTION=PARTIAL_TP1_FRACTION,
        PARTIAL_TP2_FRACTION=PARTIAL_TP2_FRACTION,
        PARTIAL_TP_SPLIT=PARTIAL_TP_SPLIT,
        BREAKEVEN_RR=BREAKEVEN_RR,
        PROFIT_LOCK_AT_TARGET_FRACTION=PROFIT_LOCK_AT_TARGET_FRACTION,
        PROFIT_LOCK_KEEP_FRACTION=PROFIT_LOCK_KEEP_FRACTION,
        OVERNIGHT_SL_BUFFER_POINTS=OVERNIGHT_SL_BUFFER_POINTS,
        POST_NEWS_SL_BUFFER_POINTS=POST_NEWS_SL_BUFFER_POINTS,
        TRAIL_ATR_MULT=TRAIL_ATR_MULT,
        STALE_QUOTE_SECONDS=STALE_QUOTE_SECONDS,
        DISCONNECT_ALERT_SECONDS=DISCONNECT_ALERT_SECONDS,
        PING_MAX_MS=PING_MAX_MS,
        EXEC_LATENCY_MAX_MS=EXEC_LATENCY_MAX_MS,
        SLIPPAGE_MAX_POINTS=SLIPPAGE_MAX_POINTS,
        SLIPPAGE_PROBE_POINTS=SLIPPAGE_PROBE_POINTS,
        BAD_TICK_POINTS=BAD_TICK_POINTS,
        MARGIN_MIN_PCT=MARGIN_MIN_PCT,
        PROPOSAL_TTL_SECONDS=PROPOSAL_TTL_SECONDS,
        MAX_CONFIRM_SLIPPAGE_POINTS=MAX_CONFIRM_SLIPPAGE_POINTS,
        MIDNIGHT_SPREAD_START_HM=MIDNIGHT_SPREAD_START_HM,
        MIDNIGHT_SPREAD_END_HM=MIDNIGHT_SPREAD_END_HM,
        DAILY_CLOSE_LOCK_MINUTES=float(DAILY_CLOSE_LOCK_MINUTES),
        DAILY_CLOSE_HOUR_UTC=DAILY_CLOSE_HOUR_UTC,
        ROLLOVER_MINUTE_START=ROLLOVER_MINUTE_START,
        ROLLOVER_MINUTE_END=ROLLOVER_MINUTE_END,
        ROLLOVER_NEWS_MINUTES=ROLLOVER_NEWS_MINUTES,
        POST_NEWS_ENTRY_WAIT_MINUTES=POST_NEWS_ENTRY_WAIT_MINUTES,
        PRE_NEWS_FREEZE_MINUTES=PRE_NEWS_FREEZE_MINUTES,
        NEWS_BLACKOUT_BEFORE_MINUTES=NEWS_BLACKOUT_BEFORE_MINUTES,
        NEWS_BLACKOUT_AFTER_MINUTES=NEWS_BLACKOUT_AFTER_MINUTES,
        NEWS_VOID_SECONDS=NEWS_VOID_SECONDS,
        FIRST_MINUTE_DEAD=FIRST_MINUTE_DEAD,
        ADR_CHASE_PCT=ADR_CHASE_PCT,
        GAP_NO_CHASE_POINTS=GAP_NO_CHASE_POINTS,
        NEWS_CANDLE_ATR_MULT=NEWS_CANDLE_ATR_MULT,
        NEWS_CANDLE_M1_POINTS=NEWS_CANDLE_M1_POINTS,
        NEWS_CANDLE_M5_ADR_FRACTION=NEWS_CANDLE_M5_ADR_FRACTION,
        NEWS_CANDLE_VOLUME_Z=NEWS_CANDLE_VOLUME_Z,
        ATR_DOUBLE_LOT_HALVE=ATR_DOUBLE_LOT_HALVE,
        EMERGENCY_MOVE_POINTS_PER_MINUTE=EMERGENCY_MOVE_POINTS_PER_MINUTE,
        MAX_REPRICE_ROUNDS=MAX_REPRICE_ROUNDS,
        LIQUIDITY_PROXIMITY_ATR=LIQUIDITY_PROXIMITY_ATR,
        ENTRY_MAX_ATR_DISTANCE=ENTRY_MAX_ATR_DISTANCE,
        TARGET_MAX_ATR_DISTANCE=TARGET_MAX_ATR_DISTANCE,
        G7_MAX_SLIPPAGE_ATR=G7_MAX_SLIPPAGE_ATR,
        LOT_DUAL_CHECK_HIGH=LOT_DUAL_CHECK_HIGH,
        LOT_DUAL_CHECK_LOW=LOT_DUAL_CHECK_LOW,
    )


def _from_config(params: Any) -> LiveRiskPolicy:
    return LiveRiskPolicy(
        RISK_PCT_DEFAULT=params.risk_pct_default / 100.0,
        RISK_PCT_MAX=params.risk_pct_max / 100.0,
        RISK_PCT_NEWS_DAY=params.risk_pct_news_day / 100.0,
        DAILY_DRAWDOWN_PCT=params.daily_drawdown_pct / 100.0,
        EQUITY_SPIKE_PCT=params.equity_spike_pct / 100.0,
        SPREAD_MAX_POINTS=params.spread_max_points,
        SPREAD_STABLE_SECONDS=params.spread_stable_seconds,
        SPREAD_MULTIPLIER_PRE_NEWS=params.spread_multiplier_pre_news,
        SPREAD_PRE_NEWS_MINUTES=params.spread_pre_news_minutes,
        COOLDOWN_CONSECUTIVE_LOSSES=int(params.cooldown_consecutive_losses),
        COOLDOWN_AFTER_TWO_LOSSES_MINUTES=params.cooldown_after_two_losses_minutes,
        COOLDOWN_AFTER_TWO_LOSSES_SESSION_MINUTES=(
            params.cooldown_after_two_losses_session_minutes
        ),
        COOLDOWN_AFTER_NEWS_STOP_MINUTES=params.cooldown_after_news_stop_minutes,
        MAX_OPEN_GOLD_POSITIONS=int(params.max_open_gold_positions),
        MIN_RR=params.min_rr,
        MIN_RR_LIVE_FILL=params.min_rr_live_fill,
        IDEA_STALE_HOURS=params.idea_stale_hours,
        PENDING_TTL_HOURS=params.pending_ttl_hours,
        TIME_STOP_HOURS=params.time_stop_hours,
        HALF_DISTANCE_FRACTION=params.half_distance_pct / 100.0,
        NEWS_SHIELD_MINUTES=params.news_shield_minutes,
        FLAT_NEAR_ENTRY_POINTS=params.flat_near_entry_points,
        PARTIAL_TP1_FRACTION=params.partial_tp1_pct / 100.0,
        PARTIAL_TP2_FRACTION=params.partial_tp2_pct / 100.0,
        PARTIAL_TP_SPLIT=(
            params.partial_tp_split_1_pct / 100.0,
            params.partial_tp_split_2_pct / 100.0,
            params.partial_tp_split_3_pct / 100.0,
        ),
        BREAKEVEN_RR=params.breakeven_rr,
        PROFIT_LOCK_AT_TARGET_FRACTION=params.profit_lock_at_target_pct / 100.0,
        PROFIT_LOCK_KEEP_FRACTION=params.profit_lock_keep_pct / 100.0,
        OVERNIGHT_SL_BUFFER_POINTS=params.overnight_sl_buffer_points,
        POST_NEWS_SL_BUFFER_POINTS=params.post_news_sl_buffer_points,
        TRAIL_ATR_MULT=params.trail_atr_mult,
        STALE_QUOTE_SECONDS=params.stale_quote_seconds,
        DISCONNECT_ALERT_SECONDS=params.disconnect_alert_seconds,
        PING_MAX_MS=params.ping_max_ms,
        EXEC_LATENCY_MAX_MS=params.exec_latency_max_ms,
        SLIPPAGE_MAX_POINTS=params.slippage_max_points,
        SLIPPAGE_PROBE_POINTS=params.slippage_probe_points,
        BAD_TICK_POINTS=params.bad_tick_points,
        MARGIN_MIN_PCT=params.margin_min_pct,
        PROPOSAL_TTL_SECONDS=params.proposal_ttl_seconds,
        MAX_CONFIRM_SLIPPAGE_POINTS=params.max_confirm_slippage_points,
        MIDNIGHT_SPREAD_START_HM=(
            int(params.midnight_spread_start_hour),
            int(params.midnight_spread_start_minute),
        ),
        MIDNIGHT_SPREAD_END_HM=(
            int(params.midnight_spread_end_hour),
            int(params.midnight_spread_end_minute),
        ),
        DAILY_CLOSE_LOCK_MINUTES=params.daily_close_lock_minutes,
        DAILY_CLOSE_HOUR_UTC=int(params.daily_close_hour_utc),
        ROLLOVER_MINUTE_START=int(params.rollover_minute_start),
        ROLLOVER_MINUTE_END=int(params.rollover_minute_end),
        ROLLOVER_NEWS_MINUTES=params.rollover_news_minutes,
        POST_NEWS_ENTRY_WAIT_MINUTES=params.post_news_entry_wait_minutes,
        PRE_NEWS_FREEZE_MINUTES=params.pre_news_freeze_minutes,
        NEWS_BLACKOUT_BEFORE_MINUTES=params.news_blackout_before_minutes,
        NEWS_BLACKOUT_AFTER_MINUTES=params.news_blackout_after_minutes,
        NEWS_VOID_SECONDS=params.news_void_seconds,
        FIRST_MINUTE_DEAD=params.first_minute_dead,
        ADR_CHASE_PCT=params.adr_chase_multiple,
        GAP_NO_CHASE_POINTS=params.gap_no_chase_points,
        NEWS_CANDLE_ATR_MULT=params.news_candle_atr_mult,
        NEWS_CANDLE_M1_POINTS=params.news_candle_m1_points,
        NEWS_CANDLE_M5_ADR_FRACTION=params.news_candle_m5_adr_pct / 100.0,
        NEWS_CANDLE_VOLUME_Z=params.news_candle_volume_z,
        ATR_DOUBLE_LOT_HALVE=params.atr_double_lot_halve,
        EMERGENCY_MOVE_POINTS_PER_MINUTE=params.emergency_move_points_per_minute,
        MAX_REPRICE_ROUNDS=int(params.max_reprice_rounds),
        LIQUIDITY_PROXIMITY_ATR=params.liquidity_proximity_atr,
        ENTRY_MAX_ATR_DISTANCE=params.entry_max_atr_distance,
        TARGET_MAX_ATR_DISTANCE=params.target_max_atr_distance,
        G7_MAX_SLIPPAGE_ATR=params.g7_max_slippage_atr,
        LOT_DUAL_CHECK_HIGH=params.lot_dual_check_high,
        LOT_DUAL_CHECK_LOW=params.lot_dual_check_low,
    )


_live_cache: tuple[str, float, LiveRiskPolicy] | None = None


def invalidate_live_cache() -> None:
    """Drop the mtime cache so the next ``live()`` call reloads config."""
    global _live_cache
    _live_cache = None


def live(config_path: Path | None = None) -> LiveRiskPolicy:
    """Return gate-unit risk parameters from the currently loaded config file."""
    global _live_cache
    try:
        from nanobot.config.loader import get_config_path, load_config

        path = (config_path or get_config_path()).expanduser()
        try:
            mtime = path.stat().st_mtime if path.exists() else 0.0
        except OSError:
            mtime = 0.0
        key = str(path)
        cached = _live_cache
        if cached is not None and cached[0] == key and cached[1] == mtime:
            return cached[2]
        params = load_config(path).trading_risk_parameters
        snapshot = _from_config(params)
        _live_cache = (key, mtime, snapshot)
        return snapshot
    except Exception:
        return _defaults()
