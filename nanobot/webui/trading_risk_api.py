"""Trading risk-parameter helpers for the WebUI settings surface.

Follows the MCP presets pattern: load_config / save_config, an error type with
HTTP status, payload + action, and a settings_action wrapper that serializes
writes through WebUISettingsConfig.run_serialized.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from nanobot.config.loader import load_config, save_config
from nanobot.config.schema import TradingRiskParameters
from nanobot.trading.i18n import tr
from nanobot.trading.policy import invalidate_live_cache
from nanobot.trading.risk_state import DEFAULT_TOGGLES, LOCKED_INTEGRITY_TOGGLES, get_risk_store

QueryParams = dict[str, list[str]]

if TYPE_CHECKING:
    from nanobot.webui.settings_services import WebUISettingsConfig

_UPDATE_ACTIONS = {"update"}


class TradingRiskError(Exception):
    """WebUI-facing trading risk parameter error."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


@dataclass(frozen=True)
class RiskFieldSpec:
    name: str
    group: str
    unit: str
    step: float = 1.0
    integer: bool = False


# Operator-facing field catalog. Defaults live on TradingRiskParameters.
RISK_FIELD_SPECS: tuple[RiskFieldSpec, ...] = (
    RiskFieldSpec("risk_pct_default", "sizing", "%", 0.1),
    RiskFieldSpec("risk_pct_max", "sizing", "%", 0.1),
    RiskFieldSpec("risk_pct_news_day", "sizing", "%", 0.1),
    RiskFieldSpec("daily_drawdown_pct", "drawdown", "%", 0.1),
    RiskFieldSpec("equity_spike_pct", "drawdown", "%", 0.1),
    RiskFieldSpec("spread_max_points", "spread", "points", 1),
    RiskFieldSpec("spread_stable_seconds", "spread", "seconds", 1),
    RiskFieldSpec("spread_multiplier_pre_news", "spread", "×", 0.1),
    RiskFieldSpec("spread_pre_news_minutes", "spread", "minutes", 0.5),
    RiskFieldSpec("cooldown_consecutive_losses", "cooldown", "count", 1, integer=True),
    RiskFieldSpec("cooldown_after_two_losses_minutes", "cooldown", "minutes", 1),
    RiskFieldSpec("cooldown_after_two_losses_session_minutes", "cooldown", "minutes", 1),
    RiskFieldSpec("cooldown_after_news_stop_minutes", "cooldown", "minutes", 1),
    RiskFieldSpec("max_open_gold_positions", "positions", "count", 1, integer=True),
    RiskFieldSpec("min_rr", "positions", "R", 0.1),
    RiskFieldSpec("min_rr_live_fill", "positions", "R", 0.1),
    RiskFieldSpec("idea_stale_hours", "pending", "hours", 0.5),
    RiskFieldSpec("pending_ttl_hours", "pending", "hours", 0.5),
    RiskFieldSpec("time_stop_hours", "pending", "hours", 0.5),
    RiskFieldSpec("half_distance_pct", "pending", "%", 1),
    RiskFieldSpec("news_shield_minutes", "news", "minutes", 1),
    RiskFieldSpec("flat_near_entry_points", "news", "points", 1),
    RiskFieldSpec("pre_news_freeze_minutes", "news", "minutes", 1),
    RiskFieldSpec("post_news_entry_wait_minutes", "news", "minutes", 1),
    RiskFieldSpec("news_blackout_before_minutes", "news", "minutes", 1),
    RiskFieldSpec("news_blackout_after_minutes", "news", "minutes", 1),
    RiskFieldSpec("news_void_seconds", "news", "seconds", 1),
    RiskFieldSpec("first_minute_dead", "news", "seconds", 1),
    RiskFieldSpec("proposal_ttl_seconds", "execution", "seconds", 1),
    RiskFieldSpec("max_confirm_slippage_points", "execution", "points", 1),
    RiskFieldSpec("slippage_max_points", "execution", "points", 1),
    RiskFieldSpec("slippage_probe_points", "execution", "points", 1),
    RiskFieldSpec("exec_latency_max_ms", "execution", "ms", 1),
    RiskFieldSpec("stale_quote_seconds", "quote", "seconds", 0.5),
    RiskFieldSpec("disconnect_alert_seconds", "quote", "seconds", 0.5),
    RiskFieldSpec("ping_max_ms", "quote", "ms", 1),
    RiskFieldSpec("bad_tick_points", "quote", "points", 1),
    RiskFieldSpec("margin_min_pct", "quote", "% margin level", 1),
    RiskFieldSpec("midnight_spread_start_hour", "session", "hour UTC", 1, integer=True),
    RiskFieldSpec("midnight_spread_start_minute", "session", "minute", 1, integer=True),
    RiskFieldSpec("midnight_spread_end_hour", "session", "hour UTC", 1, integer=True),
    RiskFieldSpec("midnight_spread_end_minute", "session", "minute", 1, integer=True),
    RiskFieldSpec("daily_close_lock_minutes", "session", "minutes", 1),
    RiskFieldSpec("daily_close_hour_utc", "session", "hour UTC", 1, integer=True),
    RiskFieldSpec("rollover_minute_start", "session", "minute", 1, integer=True),
    RiskFieldSpec("rollover_minute_end", "session", "minute", 1, integer=True),
    RiskFieldSpec("rollover_news_minutes", "session", "minutes", 1),
    RiskFieldSpec("partial_tp1_pct", "management", "%", 1),
    RiskFieldSpec("partial_tp2_pct", "management", "%", 1),
    RiskFieldSpec("partial_tp_split_1_pct", "management", "%", 1),
    RiskFieldSpec("partial_tp_split_2_pct", "management", "%", 1),
    RiskFieldSpec("partial_tp_split_3_pct", "management", "%", 1),
    RiskFieldSpec("breakeven_rr", "management", "R", 0.1),
    RiskFieldSpec("profit_lock_at_target_pct", "management", "%", 1),
    RiskFieldSpec("profit_lock_keep_pct", "management", "%", 1),
    RiskFieldSpec("overnight_sl_buffer_points", "management", "points", 1),
    RiskFieldSpec("post_news_sl_buffer_points", "management", "points", 1),
    RiskFieldSpec("trail_atr_mult", "management", "× ATR", 0.1),
    RiskFieldSpec("adr_chase_multiple", "volatility", "× ADR", 0.1),
    RiskFieldSpec("gap_no_chase_points", "volatility", "points", 1),
    RiskFieldSpec("news_candle_atr_mult", "volatility", "× ATR", 0.1),
    RiskFieldSpec("news_candle_m1_points", "volatility", "points", 1),
    RiskFieldSpec("news_candle_m5_adr_pct", "volatility", "% ADR", 1),
    RiskFieldSpec("news_candle_volume_z", "volatility", "z", 0.1),
    RiskFieldSpec("atr_double_lot_halve", "volatility", "× ATR", 0.1),
    RiskFieldSpec("emergency_move_points_per_minute", "volatility", "points/min", 1),
    RiskFieldSpec("max_reprice_rounds", "execution", "count", 1, integer=True),
    RiskFieldSpec("liquidity_proximity_atr", "positions", "× ATR", 0.05),
    RiskFieldSpec("entry_max_atr_distance", "positions", "× ATR", 0.05),
    RiskFieldSpec("target_max_atr_distance", "positions", "× ATR", 0.5),
    RiskFieldSpec("g7_max_slippage_atr", "execution", "× ATR", 0.05),
    RiskFieldSpec("lot_dual_check_high", "sizing", "× sized lot", 0.1),
    RiskFieldSpec("lot_dual_check_low", "sizing", "× sized lot", 0.1),
)

_GROUP_ORDER = (
    "sizing",
    "drawdown",
    "spread",
    "cooldown",
    "positions",
    "pending",
    "news",
    "execution",
    "quote",
    "session",
    "management",
    "volatility",
)


def _toggle_payload() -> list[dict[str, Any]]:
    snap = get_risk_store().snapshot()
    rows: list[dict[str, Any]] = []
    for name, default in DEFAULT_TOGGLES.items():
        rows.append(
            {
                "name": name,
                "label": tr(f"risk.toggle.{name}"),
                "enabled": bool(snap.feature_toggles.get(name, default)),
                "never_skips_confirm": True,
                "confirm_note": tr("risk.settings.confirm_stays"),
            }
        )
    return rows


def _query_first(query: QueryParams, key: str) -> str | None:
    values = query.get(key)
    return values[0] if values else None


def _constraints(name: str) -> dict[str, float]:
    field = TradingRiskParameters.model_fields[name]
    out: dict[str, float] = {}
    for item in field.metadata:
        ge = getattr(item, "ge", None)
        le = getattr(item, "le", None)
        gt = getattr(item, "gt", None)
        lt = getattr(item, "lt", None)
        if ge is not None:
            out["min"] = float(ge)
        if le is not None:
            out["max"] = float(le)
        if gt is not None:
            out["exclusiveMin"] = float(gt)
        if lt is not None:
            out["exclusiveMax"] = float(lt)
    return out


def _field_payload(spec: RiskFieldSpec, params: TradingRiskParameters) -> dict[str, Any]:
    value = getattr(params, spec.name)
    payload: dict[str, Any] = {
        "name": spec.name,
        "label": tr(f"risk.field.{spec.name}"),
        "group": spec.group,
        "group_label": tr(f"risk.group.{spec.group}"),
        "unit": spec.unit,
        "value": value,
        "type": "integer" if spec.integer else "number",
        "step": spec.step,
    }
    payload.update(_constraints(spec.name))
    return payload


def trading_risk_payload(
    *,
    last_action: dict[str, Any] | None = None,
    config_path: Path | None = None,
) -> dict[str, Any]:
    config = load_config(config_path) if config_path is not None else load_config()
    params = config.trading_risk_parameters
    fields = [_field_payload(spec, params) for spec in RISK_FIELD_SPECS]
    groups: list[dict[str, Any]] = []
    for group_id in _GROUP_ORDER:
        group_fields = [row for row in fields if row["group"] == group_id]
        if not group_fields:
            continue
        groups.append(
            {
                "id": group_id,
                "label": tr(f"risk.group.{group_id}"),
                "fields": group_fields,
            }
        )
    payload: dict[str, Any] = {
        "title": tr("risk.settings.title"),
        "description": tr("risk.settings.description"),
        "operator_warning": tr("risk.operator_warning"),
        "save_label": tr("risk.settings.save"),
        "loading_label": tr("risk.settings.loading"),
        "saving_label": tr("risk.settings.saving"),
        "number_required": tr("risk.settings.number_required", field="{field}"),
        "min_label": tr("risk.settings.min_label", value="{value}"),
        "max_label": tr("risk.settings.max_label", value="{value}"),
        "toggles_title": tr("risk.settings.toggles_title"),
        "toggles_help": tr("risk.settings.toggles_help"),
        "groups": groups,
        "values": params.model_dump(mode="json"),
        "toggles": _toggle_payload(),
        "locked_toggles": sorted(LOCKED_INTEGRITY),
    }
    if last_action is not None:
        payload["last_action"] = last_action
    return payload


LOCKED_INTEGRITY = frozenset(LOCKED_INTEGRITY_TOGGLES)


def _parse_json_value(raw: str | None, *, fallback: Any) -> Any:
    if raw is None or not raw.strip():
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise TradingRiskError(tr("risk.api.invalid_json", detail=exc.msg)) from exc


def _parse_updates(query: QueryParams, *, allow_empty: bool = False) -> dict[str, Any]:
    known = {spec.name for spec in RISK_FIELD_SPECS}
    integer_names = {spec.name for spec in RISK_FIELD_SPECS if spec.integer}
    updates: dict[str, Any] = {}
    raw_values = _query_first(query, "values")
    parsed = _parse_json_value(raw_values, fallback=None)
    if parsed is not None:
        if not isinstance(parsed, dict):
            raise TradingRiskError(tr("risk.api.values_object"))
        for key, value in parsed.items():
            if key in known:
                updates[key] = value
    for spec in RISK_FIELD_SPECS:
        raw = _query_first(query, spec.name)
        if raw is None or raw == "":
            continue
        try:
            updates[spec.name] = int(raw) if spec.name in integer_names else float(raw)
        except ValueError as exc:
            raise TradingRiskError(tr("risk.api.number_required", name=spec.name)) from exc
    if not updates:
        if allow_empty:
            return {}
        raise TradingRiskError(tr("risk.api.no_updates"))
    unknown = set(updates) - known
    if unknown:
        raise TradingRiskError(tr("risk.api.unknown_parameter", name=sorted(unknown)[0]))
    return updates


def _parse_toggle_updates(query: QueryParams) -> dict[str, bool]:
    raw_values = _query_first(query, "toggles")
    parsed = _parse_json_value(raw_values, fallback=None)
    if parsed is None:
        return {}
    if not isinstance(parsed, dict):
        raise TradingRiskError(tr("risk.api.toggles_object"))
    known = set(DEFAULT_TOGGLES)
    updates: dict[str, bool] = {}
    for key, value in parsed.items():
        name = str(key)
        if name in LOCKED_INTEGRITY:
            raise TradingRiskError(tr("risk.api.locked_toggle", name=name))
        if name not in known:
            raise TradingRiskError(tr("risk.api.unknown_toggle", name=name))
        updates[name] = bool(value)
    return updates


def trading_risk_action(
    action: str,
    query: QueryParams,
    *,
    config_path: Path | None = None,
) -> dict[str, Any]:
    if action != "update":
        raise TradingRiskError(tr("risk.api.unknown_action", action=action), status=404)

    config = load_config(config_path) if config_path is not None else load_config()
    toggle_updates = _parse_toggle_updates(query)
    updates = _parse_updates(query, allow_empty=bool(toggle_updates))
    if updates:
        merged = config.trading_risk_parameters.model_dump()
        merged.update(updates)
        try:
            config.trading_risk_parameters = TradingRiskParameters.model_validate(merged)
        except ValidationError as exc:
            issue = exc.errors()[0] if exc.errors() else None
            loc = ".".join(str(part) for part in issue["loc"]) if issue else "value"
            msg = issue["msg"] if issue else tr("risk.api.invalid_value", loc="value", msg="")
            raise TradingRiskError(tr("risk.api.invalid_value", loc=loc, msg=msg)) from exc
        save_config(config, config_path)
        invalidate_live_cache()
    if toggle_updates:
        get_risk_store().update(feature_toggles=toggle_updates)
    payload = trading_risk_payload(
        last_action={
            "ok": True,
            "message": tr("risk.settings.saved"),
            "updated": sorted(list(updates) + list(toggle_updates)),
        },
        config_path=config_path,
    )
    return payload


async def trading_risk_settings_action(
    action: str | None,
    query: QueryParams,
    *,
    config: WebUISettingsConfig | None = None,
) -> dict[str, Any]:
    """Run a WebUI trading-risk action and persist through the config lock."""
    config_path = config.path if config is not None else None
    if action is None:
        return trading_risk_payload(config_path=config_path)
    if action not in _UPDATE_ACTIONS:
        raise TradingRiskError(tr("risk.api.unknown_action", action=action), status=404)
    if config is not None:
        return await asyncio.to_thread(
            config.run_serialized,
            lambda path: trading_risk_action(action, query, config_path=path),
        )
    return await asyncio.to_thread(trading_risk_action, action, query)
