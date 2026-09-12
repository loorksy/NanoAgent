"""Trading runtime configuration from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class TradingConfig:
    oanda_api_token: str | None
    oanda_account_id: str | None
    oanda_env: str

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
    )
