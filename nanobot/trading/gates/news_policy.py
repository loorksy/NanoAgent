"""News gate policy (G1) — warn vs strict, from ``TradingRiskParameters.news_gate_mode``."""

from __future__ import annotations

from typing import Literal

NewsGateMode = Literal["warn", "strict", "off"]


def news_gate_mode() -> NewsGateMode:
    from nanobot.config.errors import ConfigLoadError
    from nanobot.config.loader import load_config

    try:
        raw = str(load_config().trading_risk_parameters.news_gate_mode).strip().lower()
    except (OSError, ConfigLoadError, ValueError):
        return "warn"
    if raw in {"strict", "off"}:
        return raw  # type: ignore[return-value]
    return "warn"
