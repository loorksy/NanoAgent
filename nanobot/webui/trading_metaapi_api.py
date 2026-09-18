"""WebUI helpers for linking a MetaAPI / MT5 account.

Follows the trading-risk pattern: load_config / save_config, an error type with
HTTP status, payload + action, and a settings_action wrapper that serializes
writes through WebUISettingsConfig.run_serialized. Payloads never include the
MetaAPI token or the MT5 password.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from nanobot.config.loader import load_config, save_config
from nanobot.config.schema import TradingMetaApiConfig
from nanobot.trading.config import load_trading_config
from nanobot.trading.i18n import tr
from nanobot.trading.mt5_metaapi import (
    METAAPI_REGIONS,
    get_transport,
    provision_mt5_account,
    public_account_information,
    reset_transport,
    sdk_available,
)
from nanobot.webui.settings_models import mask_secret_hint

QueryParams = dict[str, list[str]]

if TYPE_CHECKING:
    from nanobot.webui.settings_services import WebUISettingsConfig

_UPDATE_ACTIONS = frozenset({"update", "test", "disconnect"})
_SECRET_KEYS = frozenset({"token", "password", "investorPassword", "investor_password"})


class TradingMetaApiError(Exception):
    """WebUI-facing MT5 connect error."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


@dataclass
class _ConnectDraft:
    token: str
    account_id: str
    region: str
    login: str
    password: str
    server: str
    locale: str | None
    provision: bool


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
    token = (os.environ.get("METAAPI_TOKEN") or "").strip()
    account = (os.environ.get("METAAPI_ACCOUNT_ID") or "").strip()
    return bool(token or account)


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


def _labels(locale: str | None) -> dict[str, Any]:
    return {
        "title": tr("mt5.connect.title", locale=locale),
        "description": tr("mt5.connect.description", locale=locale),
        "hitl_note": tr("mt5.connect.hitl_note", locale=locale),
        "token_label": tr("mt5.connect.token_label", locale=locale),
        "token_help": tr("mt5.connect.token_help", locale=locale),
        "token_placeholder": tr("mt5.connect.token_placeholder", locale=locale),
        "token_configured_placeholder": tr(
            "mt5.connect.token_configured_placeholder", locale=locale
        ),
        "account_id_label": tr("mt5.connect.account_id_label", locale=locale),
        "account_id_help": tr("mt5.connect.account_id_help", locale=locale),
        "region_label": tr("mt5.connect.region_label", locale=locale),
        "login_label": tr("mt5.connect.login_label", locale=locale),
        "password_label": tr("mt5.connect.password_label", locale=locale),
        "server_label": tr("mt5.connect.server_label", locale=locale),
        "server_placeholder": tr("mt5.connect.server_placeholder", locale=locale),
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
            tr("mt5.connect.step_token", locale=locale),
            tr("mt5.connect.step_login", locale=locale),
            tr("mt5.connect.step_connect", locale=locale),
        ],
        "regions": [{"id": name, "label": name} for name in METAAPI_REGIONS],
    }


def _account_summary(account: dict[str, Any], locale: str | None) -> dict[str, Any]:
    login = str(account.get("login") or "")
    server = str(account.get("server") or "")
    currency = str(account.get("currency") or "")
    balance = account.get("balance")
    summary: list[str] = []
    if login:
        summary.append(tr("mt5.connect.login_value", locale=locale, login=login))
    if server:
        summary.append(tr("mt5.connect.server_value", locale=locale, server=server))
    if balance is not None:
        summary.append(
            tr(
                "mt5.connect.balance",
                locale=locale,
                balance=balance,
                currency=currency,
            )
        )
    return {**account, "summary": summary}


async def _live_account(locale: str | None) -> tuple[dict[str, Any] | None, str | None]:
    transport = get_transport()
    snapshot = await transport.account_snapshot()
    if not snapshot.get("ok"):
        detail = str(snapshot.get("error") or tr("mt5.credentials_missing", locale=locale))
        return None, detail
    info = snapshot.get("account")
    public = public_account_information(info if isinstance(info, dict) else {})
    return _account_summary(public, locale), None


def trading_metaapi_payload(
    *,
    last_action: dict[str, Any] | None = None,
    config_path: Path | None = None,
    locale: str | None = None,
    account: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = load_config(config_path) if config_path is not None else load_config()
    trading = load_trading_config()
    stored = config.trading_metaapi
    payload: dict[str, Any] = {
        **_labels(locale),
        "configured": trading.metaapi_configured,
        "token_set": bool(trading.metaapi_token),
        "token_hint": mask_secret_hint(trading.metaapi_token),
        "account_id": trading.metaapi_account_id or "",
        "region": trading.metaapi_region or "new-york",
        "sdk_available": sdk_available(),
        "env_override": _env_override(),
        "source": _source(configured=trading.metaapi_configured),
        "stored_account_id": stored.account_id,
        "account": account,
    }
    if last_action is not None:
        payload["last_action"] = last_action
    return _public_safe(payload)


def _parse_connect(query: QueryParams, *, config_path: Path | None) -> _ConnectDraft:
    locale = _locale(query)
    config = load_config(config_path) if config_path is not None else load_config()
    stored = config.trading_metaapi
    token = _query_text(query, "token") or (stored.token or "")
    account_id = _query_text(query, "account_id", "accountId") or (stored.account_id or "")
    region = (_query_text(query, "region") or stored.region or "new-york").lower()
    if region not in METAAPI_REGIONS:
        raise TradingMetaApiError(tr("mt5.connect.region_invalid", locale=locale, region=region))
    login = _query_text(query, "login")
    password = _query_text(query, "password")
    server = _query_text(query, "server")
    provision_bits = (login, password, server)
    if any(provision_bits) and not all(provision_bits):
        raise TradingMetaApiError(tr("mt5.connect.login_incomplete", locale=locale))
    provision = all(bool(part) for part in provision_bits)
    if not token:
        raise TradingMetaApiError(tr("mt5.connect.token_required", locale=locale))
    if not provision and not account_id:
        raise TradingMetaApiError(tr("mt5.connect.account_or_login_required", locale=locale))
    return _ConnectDraft(
        token=token,
        account_id=account_id,
        region=region,
        login=login,
        password=password,
        server=server,
        locale=locale,
        provision=provision,
    )


def _persist(draft: _ConnectDraft, *, config_path: Path | None) -> None:
    config = load_config(config_path) if config_path is not None else load_config()
    config.trading_metaapi = TradingMetaApiConfig(
        token=draft.token,
        account_id=draft.account_id,
        region=draft.region,
    )
    save_config(config, config_path)
    reset_transport()


def _disconnect_sync(query: QueryParams, *, config_path: Path | None) -> dict[str, Any]:
    locale = _locale(query)
    if _env_override():
        raise TradingMetaApiError(tr("mt5.connect.env_disconnect_blocked", locale=locale))
    config = load_config(config_path) if config_path is not None else load_config()
    region = config.trading_metaapi.region or "new-york"
    config.trading_metaapi = TradingMetaApiConfig(token="", account_id="", region=region)
    save_config(config, config_path)
    reset_transport()
    return trading_metaapi_payload(
        last_action={"ok": True, "message": tr("mt5.connect.disconnected", locale=locale)},
        config_path=config_path,
        locale=locale,
    )


def _saved_payload(
    *,
    config_path: Path | None,
    locale: str | None,
    account: dict[str, Any] | None,
    live_error: str | None,
) -> dict[str, Any]:
    last_action: dict[str, Any] = {
        "ok": True,
        "message": tr("mt5.connect.saved", locale=locale),
        "live_ok": live_error is None,
    }
    if live_error:
        last_action["live_error"] = live_error
    return trading_metaapi_payload(
        last_action=last_action,
        config_path=config_path,
        locale=locale,
        account=account,
    )


async def _apply_update(query: QueryParams, *, config_path: Path | None) -> dict[str, Any]:
    draft = _parse_connect(query, config_path=config_path)
    if draft.provision:
        result = await provision_mt5_account(
            token=draft.token,
            region=draft.region,
            login=draft.login,
            password=draft.password,
            server=draft.server,
        )
        if not result.get("ok"):
            locale = draft.locale
            raise TradingMetaApiError(
                str(result.get("error") or tr("mt5.sdk_missing", locale=locale))
            )
        draft.account_id = str(result.get("account_id") or "")
        if not draft.account_id:
            raise TradingMetaApiError(
                tr("mt5.connect.provision_failed", locale=draft.locale, detail="id")
            )
    _persist(draft, config_path=config_path)
    account, live_error = await _live_account(draft.locale)
    return _saved_payload(
        config_path=config_path,
        locale=draft.locale,
        account=account,
        live_error=live_error,
    )


async def trading_metaapi_action(
    action: str,
    query: QueryParams,
    *,
    config_path: Path | None = None,
) -> dict[str, Any]:
    locale = _locale(query)
    if action == "test":
        reset_transport()
        account, error = await _live_account(locale)
        if error:
            raise TradingMetaApiError(tr("mt5.connect.test_failed", locale=locale, detail=error))
        return trading_metaapi_payload(
            last_action={"ok": True, "message": tr("mt5.connect.tested", locale=locale)},
            config_path=config_path,
            locale=locale,
            account=account,
        )
    if action == "disconnect":
        return _disconnect_sync(query, config_path=config_path)
    if action != "update":
        raise TradingMetaApiError(
            tr("mt5.connect.api.unknown_action", locale=locale, action=action),
            status=404,
        )
    return await _apply_update(query, config_path=config_path)


async def trading_metaapi_settings_action(
    action: str | None,
    query: QueryParams,
    *,
    config: WebUISettingsConfig | None = None,
) -> dict[str, Any]:
    """Run a WebUI MT5-connect action and persist through the config lock."""
    config_path = config.path if config is not None else None
    locale = _locale(query)
    if action is None:
        return trading_metaapi_payload(config_path=config_path, locale=locale)
    if action not in _UPDATE_ACTIONS:
        raise TradingMetaApiError(
            tr("mt5.connect.api.unknown_action", locale=locale, action=action),
            status=404,
        )
    if config is None:
        return await trading_metaapi_action(action, query, config_path=config_path)
    if action == "test":
        return await trading_metaapi_action(action, query, config_path=config.path)
    if action == "disconnect":
        return await asyncio.to_thread(
            config.run_serialized,
            lambda path: _disconnect_sync(query, config_path=path),
        )

    draft = _parse_connect(query, config_path=config.path)
    if draft.provision:
        result = await provision_mt5_account(
            token=draft.token,
            region=draft.region,
            login=draft.login,
            password=draft.password,
            server=draft.server,
        )
        if not result.get("ok"):
            raise TradingMetaApiError(
                str(result.get("error") or tr("mt5.sdk_missing", locale=locale))
            )
        draft.account_id = str(result.get("account_id") or "")
        if not draft.account_id:
            raise TradingMetaApiError(
                tr("mt5.connect.provision_failed", locale=locale, detail="id")
            )
    await asyncio.to_thread(
        config.run_serialized,
        lambda path: _persist(draft, config_path=path),
    )
    account, live_error = await _live_account(locale)
    return _saved_payload(
        config_path=config.path,
        locale=locale,
        account=account,
        live_error=live_error,
    )
