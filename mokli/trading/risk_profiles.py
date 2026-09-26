"""Risk-profile presets and slider → dependent-field derivations (04 §4.1–§4.2).

Seven operator-facing sliders drive the rest of ``TradingRiskParameters``.
``apply_profile`` sets the sliders from a preset and re-derives; ``derive``
recomputes the dependent fields from whatever the sliders currently hold.
Derived values are clamped to the field bounds declared on the schema so any
slider position validates.
"""

from __future__ import annotations

from typing import Final, Literal

from mokli.config.schema import TradingRiskParameters

ProfileName = Literal["conservative", "balanced", "aggressive", "custom"]

PRESET_NAMES: Final[tuple[str, ...]] = ("conservative", "balanced", "aggressive")
PROFILE_NAMES: Final[tuple[str, ...]] = (*PRESET_NAMES, "custom")
DEFAULT_PROFILE: Final[str] = "balanced"

SLIDER_FIELDS: Final[tuple[str, ...]] = (
    "risk_pct_default",
    "daily_drawdown_pct",
    "max_open_gold_positions",
    "min_rr",
    "news_shield_minutes",
    "cooldown_after_two_losses_minutes",
    "spread_max_points",
)

DERIVED_FIELDS: Final[tuple[str, ...]] = (
    "risk_pct_max",
    "risk_pct_news_day",
    "equity_spike_pct",
    "max_total_lots",
    "min_rr_live_fill",
    "breakeven_rr",
    "pre_news_freeze_minutes",
    "news_blackout_before_minutes",
    "news_blackout_after_minutes",
    "post_news_entry_wait_minutes",
    "spread_pre_news_minutes",
    "cooldown_after_two_losses_session_minutes",
    "cooldown_after_news_stop_minutes",
    "cooldown_consecutive_losses",
    "spread_multiplier_pre_news",
    "flat_near_entry_points",
)

# Slider ranges from 04 §4.2: (min, max, step).
SLIDER_RANGES: Final[dict[str, tuple[float, float, float]]] = {
    "risk_pct_default": (0.25, 3.0, 0.25),
    "daily_drawdown_pct": (1.0, 6.0, 0.5),
    "max_open_gold_positions": (1, 4, 1),
    "min_rr": (1.5, 3.0, 0.25),
    "news_shield_minutes": (5.0, 45.0, 5.0),
    "cooldown_after_two_losses_minutes": (60.0, 360.0, 30.0),
    "spread_max_points": (30.0, 120.0, 5.0),
}

# 04 §4.1 — risk/trade %, daily loss %, max trades, min R:R, news caution min,
# cooldown minutes, spread tolerance points.
PROFILES: Final[dict[str, dict[str, float | int]]] = {
    "conservative": {
        "risk_pct_default": 0.5,
        "daily_drawdown_pct": 2.0,
        "max_open_gold_positions": 1,
        "min_rr": 2.5,
        "news_shield_minutes": 30.0,
        "cooldown_after_two_losses_minutes": 240.0,
        "spread_max_points": 45.0,
    },
    "balanced": {
        "risk_pct_default": 1.0,
        "daily_drawdown_pct": 3.0,
        "max_open_gold_positions": 2,
        "min_rr": 2.0,
        "news_shield_minutes": 15.0,
        "cooldown_after_two_losses_minutes": 180.0,
        "spread_max_points": 60.0,
    },
    "aggressive": {
        "risk_pct_default": 2.0,
        "daily_drawdown_pct": 5.0,
        "max_open_gold_positions": 3,
        "min_rr": 1.5,
        "news_shield_minutes": 10.0,
        "cooldown_after_two_losses_minutes": 120.0,
        "spread_max_points": 80.0,
    },
}

# Reference sizing used to turn a risk percent into a lot figure without a live
# balance: $10k account, $5.00 (500 point) gold stop, 100 oz per lot.
REFERENCE_BALANCE_USD: Final[float] = 10_000.0
REFERENCE_STOP_USD: Final[float] = 5.0
OUNCES_PER_LOT: Final[float] = 100.0
LOT_STEP: Final[float] = 0.01


def reference_lot(risk_pct: float) -> float:
    """Lot size that risks ``risk_pct`` of the reference balance on the reference stop."""
    if risk_pct <= 0:
        return 0.0
    raw = REFERENCE_BALANCE_USD * (risk_pct / 100.0) / (REFERENCE_STOP_USD * OUNCES_PER_LOT)
    return max(LOT_STEP, round(raw / LOT_STEP) * LOT_STEP)


def _bounds(name: str) -> tuple[float | None, float | None]:
    field = TradingRiskParameters.model_fields[name]
    low: float | None = None
    high: float | None = None
    for item in field.metadata:
        ge = getattr(item, "ge", None)
        le = getattr(item, "le", None)
        if ge is not None:
            low = float(ge)
        if le is not None:
            high = float(le)
    return low, high


def _clamp(name: str, value: float) -> float:
    low, high = _bounds(name)
    if low is not None and value < low:
        value = low
    if high is not None and value > high:
        value = high
    return value


def _round2(value: float) -> float:
    return round(value, 2)


def derived_values(params: TradingRiskParameters) -> dict[str, float | int]:
    """Dependent field values implied by the seven sliders (04 §4.2)."""
    risk = float(params.risk_pct_default)
    daily = float(params.daily_drawdown_pct)
    positions = int(params.max_open_gold_positions)
    rr = float(params.min_rr)
    news = float(params.news_shield_minutes)
    cooldown = float(params.cooldown_after_two_losses_minutes)
    spread = float(params.spread_max_points)
    per_position = reference_lot(risk)
    out: dict[str, float | int] = {
        "risk_pct_max": risk * 2,
        "risk_pct_news_day": risk * 0.5,
        "equity_spike_pct": daily * 0.67,
        "max_total_lots": positions * per_position if positions > 0 else 0.0,
        "min_rr_live_fill": max(0.0, rr - 0.5),
        "breakeven_rr": 1.0,
        "pre_news_freeze_minutes": news * 1.5,
        "news_blackout_before_minutes": news * 2,
        "news_blackout_after_minutes": news,
        "post_news_entry_wait_minutes": news,
        "spread_pre_news_minutes": news * 0.2,
        "cooldown_after_two_losses_session_minutes": cooldown / 3,
        "cooldown_after_news_stop_minutes": cooldown / 4,
        "cooldown_consecutive_losses": 2,
        "spread_multiplier_pre_news": 3.0,
        "flat_near_entry_points": spread * 0.5,
    }
    clamped: dict[str, float | int] = {}
    for name, value in out.items():
        bounded = _clamp(name, float(value))
        clamped[name] = int(bounded) if name == "cooldown_consecutive_losses" else _round2(bounded)
    return clamped


def derive(params: TradingRiskParameters) -> TradingRiskParameters:
    """Return a copy with every dependent field recomputed from the sliders."""
    merged = params.model_dump()
    merged.update(derived_values(params))
    return TradingRiskParameters.model_validate(merged)


def is_preset(name: str) -> bool:
    return name in PROFILES


def apply_profile(params: TradingRiskParameters, name: str) -> TradingRiskParameters:
    """Set the sliders from a preset and re-derive. ``custom`` only tags the profile."""
    if name == "custom":
        return params.model_copy(update={"risk_profile": "custom"})
    preset = PROFILES.get(name)
    if preset is None:
        raise KeyError(name)
    merged = params.model_dump()
    merged.update(preset)
    merged["risk_profile"] = name
    return derive(TradingRiskParameters.model_validate(merged))


def matches_preset(params: TradingRiskParameters, name: str) -> bool:
    """True when every slider equals the preset value (tolerant to float noise)."""
    preset = PROFILES.get(name)
    if preset is None:
        return False
    for field_name, expected in preset.items():
        actual = float(getattr(params, field_name))
        if abs(actual - float(expected)) > 1e-9:
            return False
    return True


def detect_profile(params: TradingRiskParameters) -> str:
    """Name of the preset whose sliders match ``params``, else ``custom``."""
    for name in PRESET_NAMES:
        if matches_preset(params, name):
            return name
    return "custom"
