"""Trading runtime configuration from saved Config, with env overrides."""

from __future__ import annotations

import os
from dataclasses import dataclass


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


@dataclass(frozen=True)
class _StoredCredentials:
    metaapi_token: str | None = None
    metaapi_account: str | None = None
    metaapi_region: str | None = None
    oanda_token: str | None = None
    oanda_account: str | None = None
    oanda_env: str | None = None


def _stored_credentials() -> _StoredCredentials:
    """Primary source: ``Config.trading_metaapi`` / ``Config.trading_oanda`` in config.json.

    Tokens fall back to the encrypted secret store via ``effective_token()``.
    """
    from mokli.config.loader import load_config

    config = load_config()
    metaapi = config.trading_metaapi
    oanda = config.trading_oanda
    return _StoredCredentials(
        metaapi_token=_strip(metaapi.effective_token()),
        metaapi_account=_strip(metaapi.account_id),
        metaapi_region=_strip(metaapi.region),
        oanda_token=_strip(oanda.effective_token()),
        oanda_account=_strip(oanda.account_id),
        oanda_env=_strip(oanda.env),
    )


def load_trading_config() -> TradingConfig:
    from mokli.config.errors import ConfigLoadError

    try:
        stored = _stored_credentials()
    except (OSError, ConfigLoadError, ValueError):
        stored = _StoredCredentials()

    # METAAPI_* / OANDA_* env vars override saved Config.
    return TradingConfig(
        oanda_api_token=_strip(os.environ.get("OANDA_API_TOKEN")) or stored.oanda_token,
        oanda_account_id=_strip(os.environ.get("OANDA_ACCOUNT_ID")) or stored.oanda_account,
        oanda_env=_strip(os.environ.get("OANDA_ENV")) or stored.oanda_env or "practice",
        metaapi_token=_strip(os.environ.get("METAAPI_TOKEN")) or stored.metaapi_token,
        metaapi_account_id=_strip(os.environ.get("METAAPI_ACCOUNT_ID")) or stored.metaapi_account,
        metaapi_region=_strip(os.environ.get("METAAPI_REGION")) or stored.metaapi_region or "new-york",
    )
