"""Trading runtime configuration from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env_flag(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


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


def load_trading_config() -> TradingConfig:
    return TradingConfig(
        oanda_api_token=os.environ.get("OANDA_API_TOKEN", "").strip() or None,
        oanda_account_id=os.environ.get("OANDA_ACCOUNT_ID", "").strip() or None,
        oanda_env=os.environ.get("OANDA_ENV", "practice").strip() or "practice",
        metaapi_token=os.environ.get("METAAPI_TOKEN", "").strip() or None,
        metaapi_account_id=os.environ.get("METAAPI_ACCOUNT_ID", "").strip() or None,
        metaapi_region=os.environ.get("METAAPI_REGION", "new-york").strip() or "new-york",
        planner_shadow_mode=_env_flag("LONORA_PLANNER_SHADOW", default=True),
        agent_first_mode=_env_flag("LONORA_AGENT_FIRST", default=True),
    )
