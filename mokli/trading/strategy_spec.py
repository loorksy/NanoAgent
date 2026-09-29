"""Structured strategy specs interpreted by the existing candle replay.

The model never supplies Python. A description becomes a fixed rule set, and
``replay`` is the only executor.
"""

from __future__ import annotations

import re
from typing import Any

_HOUR_HIGH = re.compile(
    r"قمة الساعة|كسر قمة|previous hour high|prior hour high|hour high",
    re.IGNORECASE,
)
_TREND_4H = re.compile(
    r"أربع ساعات|الاربع ساعات|الأربع ساعات|4\s*h|4\s*hour|four hour|تأكيد الاتجاه",
    re.IGNORECASE,
)
_SWING = re.compile(r"آخر قاع|اخر قاع|swing low|last low|خلف آخر|خلف اخر", re.IGNORECASE)
_RISK = re.compile(r"(\d+(?:\.\d+)?)\s*%|مخاطرة\s*(\d+(?:\.\d+)?)")
_GOLD = re.compile(r"ذهب|gold|xau", re.IGNORECASE)
_FREE_CODE = re.compile(r"```|exec\s*\(|import\s+\w+", re.IGNORECASE)


def spec_from_description(text: str, *, name: str = "") -> dict[str, Any]:
    """Pull the supported gold-breakout fields out of a natural-language description."""
    raw = text or ""
    risk_match = _RISK.search(raw)
    risk_percent: float | None = None
    if risk_match:
        token = risk_match.group(1) or risk_match.group(2)
        risk_percent = float(token)
    instrument = "XAUUSD" if _GOLD.search(raw) else ""
    entry = "break_prior_high" if _HOUR_HIGH.search(raw) else ""
    confirm = "higher_timeframe_up" if _TREND_4H.search(raw) else ""
    stop = "last_swing_low" if _SWING.search(raw) else ""
    spec: dict[str, Any] = {
        "name": name.strip() or "gold_hour_break",
        "description": raw.strip(),
        "instrument": instrument,
        "entry": entry,
        "exit": "target_or_stop",
        "stop": stop,
        "targets": "2R",
        "money_management": f"{risk_percent}%" if risk_percent is not None else "",
        "risk_percent": risk_percent,
        "entry_timeframe": "1h" if entry else "",
        "confirm_timeframe": "4h" if confirm else "",
        "tools": ["replay"],
        "variables": {
            "lookback": 5,
            "confirm_bars": 4,
            "target_rr": 2.0,
        },
        "version": 1,
        "changelog": ["designed from description"],
        "run_state": "designed",
        "free_code": bool(_FREE_CODE.search(raw)),
    }
    spec["logic_errors"] = check_logic(spec)
    spec["logic_ok"] = not spec["logic_errors"]
    return spec


def check_logic(spec: dict[str, Any]) -> list[str]:
    """Reject incomplete specs and any request to run model-written code."""
    errors: list[str] = []
    if spec.get("free_code"):
        errors.append("free_code_refused")
    if spec.get("instrument") != "XAUUSD":
        errors.append("instrument_required")
    if spec.get("entry") != "break_prior_high":
        errors.append("entry_required")
    if spec.get("stop") != "last_swing_low":
        errors.append("stop_required")
    if spec.get("confirm_timeframe") != "4h":
        errors.append("confirm_required")
    risk = spec.get("risk_percent")
    if isinstance(risk, bool) or not isinstance(risk, (int, float)):
        errors.append("risk_required")
    elif not 0 < float(risk) <= 2:
        errors.append("risk_out_of_policy")
    return errors


def rules_from_spec(spec: dict[str, Any]) -> dict[str, Any]:
    variables = spec.get("variables") if isinstance(spec.get("variables"), dict) else {}
    return {
        "name": spec.get("name") or "spec",
        "entry": spec.get("entry"),
        "lookback": int(variables.get("lookback") or 5),
        "confirm_bars": int(variables.get("confirm_bars") or 4),
        "target_rr": float(variables.get("target_rr") or 2.0),
        "risk_percent": spec.get("risk_percent"),
    }


def program_for(spec: dict[str, Any]) -> dict[str, Any]:
    """Interpreter payload. This is data, not source that gets executed."""
    return {
        "version": spec.get("version") or 1,
        "interpreter": "mokli.trading.backtest.engine",
        "rules": rules_from_spec(spec),
    }
