"""Trading runtime configuration from saved Config, with env overrides."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from loguru import logger

UnifiedLoopMode = Literal["off", "shadow", "on"]


def _env_flag(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_unified_loop() -> UnifiedLoopMode:
    raw = os.environ.get("LONORA_UNIFIED_LOOP")
    if raw is None or not raw.strip():
        return "off"
    value = raw.strip().lower()
    if value in {"off", "shadow", "on"}:
        return value  # type: ignore[return-value]
    logger.error("Invalid LONORA_UNIFIED_LOOP={} — falling back to off", raw)
    return "off"


def _env_shadow_sample() -> int:
    raw = os.environ.get("LONORA_UNIFIED_LOOP_SHADOW_SAMPLE")
    if raw is None or not raw.strip():
        return 10
    try:
        parsed = int(raw.strip())
    except ValueError:
        logger.error(
            "Invalid LONORA_UNIFIED_LOOP_SHADOW_SAMPLE={} — falling back to 10",
            raw,
        )
        return 10
    return max(0, min(100, parsed))


def _strip(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


@dataclass(frozen=True)
class TradingConfig:
    oanda_api_token: str | None
    oanda_account_id: str | None
    oanda_env: str
    metaapi_token: str | None = None
    metaapi_account_id: str | None = None
    metaapi_region: str = "new-york"
    planner_shadow_mode: bool = True
    agent_first_mode: bool = True
    unified_loop_mode: UnifiedLoopMode = "off"
    unified_loop_shadow_sample: int = 10

    @property
    def metaapi_configured(self) -> bool:
        return bool(self.metaapi_token and self.metaapi_account_id)

    @property
    def oanda_configured(self) -> bool:
        return bool(self.oanda_api_token)

    @property
    def oanda_base_url(self) -> str:
        env = (self.oanda_env or "practice").lower()
        if env == "live":
            return "https://api-fxtrade.oanda.com"
        return "https://api-fxpractice.oanda.com"

    def public_metaapi(self) -> dict[str, str | bool]:
        """Operator-safe MetaAPI snapshot — never includes the token."""
        return {
            "configured": self.metaapi_configured,
            "account_id": self.metaapi_account_id or "",
            "region": self.metaapi_region,
            "token_set": bool(self.metaapi_token),
        }


def _stored_metaapi() -> tuple[str | None, str | None, str | None]:
    """Primary source: Config.trading_metaapi persisted in config.json."""
    from nanobot.config.loader import load_config

    config = load_config()
    stored = config.trading_metaapi
    return (
        _strip(stored.token),
        _strip(stored.account_id),
        _strip(stored.region),
    )


def load_trading_config() -> TradingConfig:
    stored_token = stored_account = stored_region = None
    from nanobot.config.errors import ConfigLoadError

    try:
        stored_token, stored_account, stored_region = _stored_metaapi()
    except (OSError, ConfigLoadError, ValueError):
        stored_token = stored_account = stored_region = None

    # METAAPI_* env vars override saved Config (same pattern as OANDA_*).
    token = _strip(os.environ.get("METAAPI_TOKEN")) or stored_token
    account_id = _strip(os.environ.get("METAAPI_ACCOUNT_ID")) or stored_account
    region = (
        _strip(os.environ.get("METAAPI_REGION"))
        or stored_region
        or "new-york"
    )
    agent_first = _env_flag("LONORA_AGENT_FIRST", default=True)
    unified_mode = _env_unified_loop()
    if unified_mode == "on" and not agent_first:
        logger.error(
            "Invalid combo LONORA_UNIFIED_LOOP=on with LONORA_AGENT_FIRST=false "
            "— falling back to unified_loop_mode=off"
        )
        unified_mode = "off"

    return TradingConfig(
        oanda_api_token=_strip(os.environ.get("OANDA_API_TOKEN")),
        oanda_account_id=_strip(os.environ.get("OANDA_ACCOUNT_ID")),
        oanda_env=_strip(os.environ.get("OANDA_ENV")) or "practice",
        metaapi_token=token,
        metaapi_account_id=account_id,
        metaapi_region=region,
        planner_shadow_mode=_env_flag("LONORA_PLANNER_SHADOW", default=True),
        agent_first_mode=agent_first,
        unified_loop_mode=unified_mode,
        unified_loop_shadow_sample=_env_shadow_sample(),
    )


def unified_loop_mode() -> UnifiedLoopMode:
    """Effective unified-loop mode after invalid-combo fallback."""
    return load_trading_config().unified_loop_mode


def unified_loop_active() -> bool:
    """True when the unified loop is in shadow or on (hooks may run)."""
    return unified_loop_mode() != "off"


def unified_loop_serving() -> bool:
    """True only when the unified loop is the serving path (mode == on)."""
    return unified_loop_mode() == "on"


def peek_unified_loop_env() -> UnifiedLoopMode | None:
    """Cheap env peek. None means unset/off without loading Config.

    Callers must still use unified_loop_mode() when this returns a non-off
    candidate, because on + LONORA_AGENT_FIRST=false falls back to off.
    """
    raw = os.environ.get("LONORA_UNIFIED_LOOP")
    if raw is None or not raw.strip():
        return None
    value = raw.strip().lower()
    if value == "off":
        return None
    if value in {"shadow", "on"}:
        return value  # type: ignore[return-value]
    return "off"
