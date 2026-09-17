"""Trading runtime configuration from saved Config, with env overrides."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env_flag(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


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
    return TradingConfig(
        oanda_api_token=_strip(os.environ.get("OANDA_API_TOKEN")),
        oanda_account_id=_strip(os.environ.get("OANDA_ACCOUNT_ID")),
        oanda_env=_strip(os.environ.get("OANDA_ENV")) or "practice",
        metaapi_token=token,
        metaapi_account_id=account_id,
        metaapi_region=region,
        planner_shadow_mode=_env_flag("LONORA_PLANNER_SHADOW", default=True),
        agent_first_mode=_env_flag("LONORA_AGENT_FIRST", default=True),
    )
