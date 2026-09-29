"""Trading runtime configuration from saved Config, with env overrides."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


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
    metaapi_token: str | None = field(default=None, repr=False)
    metaapi_account_id: str | None = None
    metaapi_region: str = "new-york"
    mt5_host: str = "localhost"
    mt5_port: int = 8001
    mt5_login: str | None = None
    mt5_password: str | None = field(default=None, repr=False)
    mt5_server: str | None = None
    mt5_access: str | None = field(default=None, repr=False)
    mt5_terminal_session: bool = False

    @property
    def mt5_configured(self) -> bool:
        if not (self.mt5_login and self.mt5_server):
            return False
        return bool(self.mt5_password or self.mt5_terminal_session)

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

    def public_mt5(self) -> dict[str, str | int | bool]:
        """Operator-safe MT5 snapshot — never includes the password."""
        return {
            "configured": self.mt5_configured,
            "host": self.mt5_host,
            "port": self.mt5_port,
            "login": self.mt5_login or "",
            "server": self.mt5_server or "",
            "password_set": bool(self.mt5_password),
            "terminal_session": self.mt5_terminal_session,
        }


@dataclass(frozen=True)
class _StoredCredentials:
    mt5_host: str | None = None
    mt5_port: int | None = None
    mt5_login: str | None = None
    mt5_password: str | None = None
    mt5_server: str | None = None
    mt5_access: str | None = None
    mt5_terminal_session: bool = False
    oanda_token: str | None = None
    oanda_account: str | None = None
    oanda_env: str | None = None
    metaapi_token: str | None = None
    metaapi_account: str | None = None
    metaapi_region: str | None = None


def _stored_credentials() -> _StoredCredentials:
    """Primary source: ``Config.trading_mt5`` / ``Config.trading_oanda`` in config.json.

    The MT5 password lives only in the encrypted secret store.
    """
    from mokli.config.loader import load_config

    config = load_config()
    mt5 = config.trading_mt5
    oanda = config.trading_oanda
    metaapi = config.trading_metaapi
    return _StoredCredentials(
        mt5_host=_strip(mt5.host),
        mt5_port=int(mt5.port or 8001),
        mt5_login=_strip(mt5.login),
        mt5_password=_strip(mt5.effective_password()),
        mt5_server=_strip(mt5.server),
        mt5_access=_strip(mt5.access),
        mt5_terminal_session=bool(mt5.terminal_session),
        oanda_token=_strip(oanda.effective_token()),
        oanda_account=_strip(oanda.account_id),
        oanda_env=_strip(oanda.env),
        metaapi_token=_strip(metaapi.effective_token()),
        metaapi_account=_strip(metaapi.account_id),
        metaapi_region=_strip(metaapi.region),
    )


def _env_port(stored: int | None) -> int:
    raw = _strip(os.environ.get("MT5_PORT"))
    if raw is None:
        return stored or 8001
    try:
        port = int(raw)
    except ValueError:
        return stored or 8001
    if port < 1 or port > 65535:
        return stored or 8001
    return port


def load_trading_config() -> TradingConfig:
    from mokli.config.errors import ConfigLoadError

    try:
        stored = _stored_credentials()
    except (OSError, ConfigLoadError, ValueError):
        stored = _StoredCredentials()

    # MT5_* / OANDA_* env vars override saved Config. Host and port default when unset.
    # A stored access address belongs to the stored server name. A different
    # MT5_SERVER must not keep dialing the previous broker.
    env_server = _strip(os.environ.get("MT5_SERVER"))
    server = env_server or stored.mt5_server
    env_access = _strip(os.environ.get("MT5_ACCESS"))
    if env_access:
        access = env_access
    elif server and server == stored.mt5_server:
        access = stored.mt5_access
    else:
        access = None
    return TradingConfig(
        oanda_api_token=_strip(os.environ.get("OANDA_API_TOKEN")) or stored.oanda_token,
        oanda_account_id=_strip(os.environ.get("OANDA_ACCOUNT_ID")) or stored.oanda_account,
        oanda_env=_strip(os.environ.get("OANDA_ENV")) or stored.oanda_env or "practice",
        metaapi_token=_strip(os.environ.get("METAAPI_TOKEN")) or stored.metaapi_token,
        metaapi_account_id=_strip(os.environ.get("METAAPI_ACCOUNT_ID")) or stored.metaapi_account,
        metaapi_region=(
            _strip(os.environ.get("METAAPI_REGION")) or stored.metaapi_region or "new-york"
        ),
        mt5_host=_strip(os.environ.get("MT5_HOST")) or stored.mt5_host or "localhost",
        mt5_port=_env_port(stored.mt5_port),
        mt5_login=_strip(os.environ.get("MT5_LOGIN")) or stored.mt5_login,
        mt5_password=_strip(os.environ.get("MT5_PASSWORD")) or stored.mt5_password,
        mt5_server=server,
        mt5_access=access,
        mt5_terminal_session=stored.mt5_terminal_session,
    )
