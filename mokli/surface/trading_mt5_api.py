"""Mokli helpers for linking a self-hosted MT5 terminal.

Payloads never include the MT5 password. A successful update calls
``connect()`` and ``get_account_info()`` before anything is stored.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from mokli.config.loader import load_config, save_config
from mokli.config.schema import TradingMt5Config
from mokli.security.secret_store import get_secret_store
from mokli.trading.config import load_trading_config
from mokli.trading.i18n import tr
from mokli.trading.mt5_broker import (
    Mt5LinuxBroker,
    public_account_information,
    reset_transport,
    sdk_available,
)

QueryParams = dict[str, list[str]]

if TYPE_CHECKING:
    from mokli.surface.settings_services import MokliSettingsConfig

_UPDATE_ACTIONS = frozenset({"update", "test", "disconnect", "status"})
_SECRET_KEYS = frozenset({"password", "token", "investorPassword", "investor_password"})
_ENV_KEYS = ("MT5_LOGIN", "MT5_PASSWORD", "MT5_SERVER")


class TradingMt5Error(Exception):
    """Mokli-facing MT5 connect error."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


@dataclass
class _ConnectDraft:
    host: str
    port: int
    login: str
    password: str
    server: str
    locale: str | None


def _query_first(query: QueryParams, key: str) -> str | None:
    values = query.get(key)
    return values[0] if values else None


def _query_text(query: QueryParams, *keys: str) -> str:
    for key in keys:
        raw = _query_first(query, key)
        if raw is None:
            continue
        text = raw.strip()
        if text:
            return text
    return ""


def _locale(query: QueryParams) -> str | None:
    return _query_first(query, "locale")


def _env_override() -> bool:
    return any((os.environ.get(name) or "").strip() for name in _ENV_KEYS)


def _source(*, configured: bool) -> str:
    if _env_override():
        return "env"
    if configured:
        return "config"
    return "none"


def _public_safe(payload: dict[str, Any]) -> dict[str, Any]:
    for key in _SECRET_KEYS:
        payload.pop(key, None)
    return payload


def _port(raw: str, *, locale: str | None, fallback: int) -> int:
    text = raw.strip()
    if not text:
        return fallback
    try:
        port = int(text)
    except ValueError as exc:
        raise TradingMt5Error(tr("mt5.connect.port_invalid", locale=locale)) from exc
    if port < 1 or port > 65535:
        raise TradingMt5Error(tr("mt5.connect.port_invalid", locale=locale))
    return port


def _labels(locale: str | None) -> dict[str, Any]:
    return {
        "title": tr("mt5.connect.title", locale=locale),
        "description": tr("mt5.connect.description", locale=locale),
        "hitl_note": tr("mt5.connect.hitl_note", locale=locale),
        "login_label": tr("mt5.connect.login_label", locale=locale),
        "password_label": tr("mt5.connect.password_label", locale=locale),
        "server_label": tr("mt5.connect.server_label", locale=locale),
        "server_placeholder": tr("mt5.connect.server_placeholder", locale=locale),
        "host_label": tr("mt5.connect.host_label", locale=locale),
        "port_label": tr("mt5.connect.port_label", locale=locale),
        "advanced_label": tr("mt5.connect.advanced_label", locale=locale),
        "connect_label": tr("mt5.connect.connect_label", locale=locale),
        "test_label": tr("mt5.connect.test_label", locale=locale),
        "disconnect_label": tr("mt5.connect.disconnect_label", locale=locale),
        "saving_label": tr("mt5.connect.saving_label", locale=locale),
        "testing_label": tr("mt5.connect.testing_label", locale=locale),
        "not_connected_label": tr("mt5.connect.not_connected", locale=locale),
        "connected_label": tr("mt5.connect.connected", locale=locale),
        "env_override_warning": tr("mt5.connect.env_override", locale=locale),
        "sdk_missing_label": tr("mt5.sdk_missing", locale=locale),
        "steps": [
            tr("mt5.connect.step_terminal", locale=locale),
            tr("mt5.connect.step_login", locale=locale),
            tr("mt5.connect.step_connect", locale=locale),
        ],
    }


def _account_summary(account: dict[str, Any], locale: str | None) -> dict[str, Any]:
    login = str(account.get("login") or "")
    name = str(account.get("name") or "")
    server = str(account.get("server") or "")
    currency = str(account.get("currency") or "")
    balance = account.get("balance")
    summary: list[str] = []
    if name:
        summary.append(tr("mt5.connect.name_value", locale=locale, name=name))
    if login:
        summary.append(tr("mt5.connect.login_value", locale=locale, login=login))
    if server:
        summary.append(tr("mt5.connect.server_value", locale=locale, server=server))
    if balance is not None:
        summary.append(
            tr("mt5.connect.balance", locale=locale, balance=balance, currency=currency)
        )
    return {**account, "summary": summary}


def trading_mt5_payload(
    *,
    last_action: dict[str, Any] | None = None,
    config_path: Path | None = None,
    locale: str | None = None,
    account: dict[str, Any] | None = None,
    connected: bool | None = None,
) -> dict[str, Any]:
    config = load_config(config_path) if config_path is not None else load_config()
    trading = load_trading_config()
    stored = config.trading_mt5
    payload: dict[str, Any] = {
        **_labels(locale),
        "configured": trading.mt5_configured,
        "connected": bool(connected) if connected is not None else False,
        "password_set": bool(trading.mt5_password),
        "login": trading.mt5_login or "",
        "server": trading.mt5_server or "",
        "host": trading.mt5_host,
        "port": trading.mt5_port,
        "sdk_available": sdk_available(),
        "env_override": _env_override(),
        "source": _source(configured=trading.mt5_configured),
        "stored_login": stored.login,
        "account": account,
    }
    if isinstance(account, dict):
        account = _account_summary(public_account_information(account), locale)
        payload["account"] = account
    if last_action is not None:
        payload["last_action"] = last_action
    return _public_safe(payload)


def _parse_connect(query: QueryParams, *, config_path: Path | None) -> _ConnectDraft:
    locale = _locale(query)
    config = load_config(config_path) if config_path is not None else load_config()
    stored = config.trading_mt5
    login = _query_text(query, "login") or (stored.login or "")
    server = _query_text(query, "server") or (stored.server or "")
    # The form omits host and port unless the operator opens the advanced
    # fields. Use the same bridge address the agent uses, including MT5_HOST.
    runtime = load_trading_config()
    host = _query_text(query, "host") or runtime.mt5_host
    port = _port(_query_text(query, "port"), locale=locale, fallback=int(runtime.mt5_port))
    password = _query_text(query, "password") or stored.effective_password()
    if not login or not password or not server:
        raise TradingMt5Error(tr("mt5.connect.login_incomplete", locale=locale))
    return _ConnectDraft(
        host=host,
        port=port,
        login=login,
        password=password,
        server=server,
        locale=locale,
    )


def _persist(draft: _ConnectDraft, *, config_path: Path | None) -> None:
    config = load_config(config_path) if config_path is not None else load_config()
    get_secret_store().set("mt5_password", draft.password)
    config.trading_mt5 = TradingMt5Config(
        host=draft.host,
        port=draft.port,
        login=draft.login,
        server=draft.server,
    )
    save_config(config, config_path)
    reset_transport()


def _disconnect_sync(query: QueryParams, *, config_path: Path | None) -> dict[str, Any]:
    locale = _locale(query)
    if _env_override():
        raise TradingMt5Error(tr("mt5.connect.env_disconnect_blocked", locale=locale))
    config = load_config(config_path) if config_path is not None else load_config()
    stored = config.trading_mt5
    get_secret_store().delete("mt5_password")
    config.trading_mt5 = TradingMt5Config(host=stored.host, port=stored.port, login="", server="")
    save_config(config, config_path)
    reset_transport()
    return trading_mt5_payload(
        last_action={"ok": True, "message": tr("mt5.connect.disconnected", locale=locale)},
        config_path=config_path,
        locale=locale,
        connected=False,
    )


async def _validate_live(draft: _ConnectDraft) -> dict[str, Any]:
    if not sdk_available():
        raise TradingMt5Error(tr("mt5.sdk_missing", locale=draft.locale))
    broker = Mt5LinuxBroker(
        host=draft.host,
        port=draft.port,
        login=draft.login,
        password=draft.password,
        server=draft.server,
        attempts=1,
        retry_delay=0,
    )
    connected = await broker.connect()
    if not connected.get("ok"):
        detail = str(connected.get("error") or tr("mt5.connect.failed", locale=draft.locale))
        raise TradingMt5Error(
            tr("mt5.connect.test_failed", locale=draft.locale, detail=detail)
        )
    info = await broker.get_account_info()
    if not info.get("ok"):
        detail = str(info.get("error") or tr("mt5.connect.failed", locale=draft.locale))
        raise TradingMt5Error(
            tr("mt5.connect.test_failed", locale=draft.locale, detail=detail)
        )
    account = info.get("account")
    return _account_summary(
        public_account_information(account if isinstance(account, dict) else {}),
        draft.locale,
    )


async def _probe(locale: str | None, *, attempts: int) -> tuple[dict[str, Any] | None, str | None, bool]:
    trading = load_trading_config()
    if not trading.mt5_configured:
        return None, tr("mt5.credentials_missing", locale=locale), False
    if not sdk_available():
        return None, tr("mt5.sdk_missing", locale=locale), False
    broker = Mt5LinuxBroker.from_config(trading, attempts=attempts, retry_delay=0.2)
    connected = await broker.connect()
    if not connected.get("ok"):
        return None, str(connected.get("error") or tr("mt5.connect.failed", locale=locale)), False
    info = await broker.get_account_info()
    if not info.get("ok"):
        return None, str(info.get("error") or tr("mt5.connect.failed", locale=locale)), False
    account = info.get("account")
    public = public_account_information(account if isinstance(account, dict) else {})
    return _account_summary(public, locale), None, True


def _saved_payload(
    *,
    config_path: Path | None,
    locale: str | None,
    account: dict[str, Any] | None,
) -> dict[str, Any]:
    return trading_mt5_payload(
        last_action={"ok": True, "message": tr("mt5.connect.saved", locale=locale), "live_ok": True},
        config_path=config_path,
        locale=locale,
        account=account,
        connected=True,
    )


async def _apply_update(query: QueryParams, *, config_path: Path | None) -> dict[str, Any]:
    locale = _locale(query)
    if _env_override():
        raise TradingMt5Error(tr("mt5.connect.env_override", locale=locale))
    draft = _parse_connect(query, config_path=config_path)
    account = await _validate_live(draft)
    _persist(draft, config_path=config_path)
    return _saved_payload(config_path=config_path, locale=draft.locale, account=account)


async def trading_mt5_action(
    action: str,
    query: QueryParams,
    *,
    config_path: Path | None = None,
) -> dict[str, Any]:
    locale = _locale(query)
    if action == "status":
        account, error, connected = await _probe(locale, attempts=1)
        last_action = None
        if error and load_trading_config().mt5_configured:
            last_action = {"ok": False, "message": error}
        return trading_mt5_payload(
            last_action=last_action,
            config_path=config_path,
            locale=locale,
            account=account,
            connected=connected,
        )
    if action == "test":
        reset_transport()
        account, error, connected = await _probe(locale, attempts=3)
        if error or not connected:
            raise TradingMt5Error(
                tr("mt5.connect.test_failed", locale=locale, detail=error or "")
            )
        return trading_mt5_payload(
            last_action={"ok": True, "message": tr("mt5.connect.tested", locale=locale)},
            config_path=config_path,
            locale=locale,
            account=account,
            connected=True,
        )
    if action == "disconnect":
        return _disconnect_sync(query, config_path=config_path)
    if action != "update":
        raise TradingMt5Error(
            tr("mt5.connect.api.unknown_action", locale=locale, action=action),
            status=404,
        )
    return await _apply_update(query, config_path=config_path)


async def trading_mt5_settings_action(
    action: str | None,
    query: QueryParams,
    *,
    config: MokliSettingsConfig | None = None,
) -> dict[str, Any]:
    """Run a Mokli MT5-connect action and persist through the config lock."""
    config_path = config.path if config is not None else None
    locale = _locale(query)
    if action is None:
        return trading_mt5_payload(config_path=config_path, locale=locale)
    if action not in _UPDATE_ACTIONS:
        raise TradingMt5Error(
            tr("mt5.connect.api.unknown_action", locale=locale, action=action),
            status=404,
        )
    if action == "status":
        return await trading_mt5_action("status", query, config_path=config_path)
    if config is None or action == "test":
        return await trading_mt5_action(action, query, config_path=config_path)
    if action == "disconnect":
        return await asyncio.to_thread(
            config.run_serialized,
            lambda path: _disconnect_sync(query, config_path=path),
        )
    if _env_override():
        raise TradingMt5Error(tr("mt5.connect.env_override", locale=locale))
    draft = _parse_connect(query, config_path=config.path)
    account = await _validate_live(draft)
    await asyncio.to_thread(
        config.run_serialized,
        lambda path: _persist(draft, config_path=path),
    )
    return _saved_payload(config_path=config.path, locale=locale, account=account)
