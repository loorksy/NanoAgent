"""Link a broker account through MetaAPI using the existing login form.

The operator token stays in config or ``METAAPI_TOKEN``. The broker password
is sent to MetaAPI and is not written to Mokli config.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx

from mokli.config.loader import load_config, save_config
from mokli.trading.i18n import tr
from mokli.trading.metaapi_market import REGIONS
from mokli.trading.mt5_directory import Mt5DirectoryError, search_companies

_BASE = "https://mt-provisioning-api-v1.agiliumtrade.agiliumtrade.ai"
_MAGIC = 880011
_TIMEOUT = 20.0
_MAX_COMPANIES = 30
_MAX_SERVERS = 40


class MetaApiLinkError(Exception):
    """The MetaAPI link form could not finish."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


def search_brokers(query: str, *, locale: str | None = None) -> list[dict[str, Any]]:
    """Companies and server names for the broker picker."""
    text = query.strip()
    if len(text) < 2:
        return []
    token = _token()
    if token:
        try:
            companies = _group(_known_servers(text, token))
        except MetaApiLinkError:
            companies = []
        if companies:
            return companies
    try:
        rows = search_companies(text)
    except Mt5DirectoryError as exc:
        raise MetaApiLinkError(
            tr("metaapi.connect.directory_failed", locale=locale),
            status=502,
        ) from exc
    return [row for row in rows if isinstance(row, dict)]


def link_account(
    *,
    login: str,
    password: str,
    server: str,
    config_path: Path | None = None,
    locale: str | None = None,
    company: str = "",
) -> dict[str, Any]:
    """Create and deploy a MetaAPI cloud account, then store its id."""
    _reject_env_override(locale)
    account_login = login.strip()
    account_server = server.strip()
    secret = password
    if not account_login or not secret.strip() or not account_server:
        raise MetaApiLinkError(tr("metaapi.connect.incomplete", locale=locale))
    token = _require_token(locale, config_path)
    region = _stored_region(config_path)
    created = _provision(
        token,
        login=account_login,
        password=secret,
        server=account_server,
        name=(company or account_login).strip() or account_login,
        region=region,
        locale=locale,
    )
    account_id = _account_id(created)
    if not account_id:
        raise MetaApiLinkError(tr("metaapi.connect.failed", locale=locale), status=502)
    try:
        _deploy(token, account_id, locale=locale)
        live = _read(token, account_id)
    except MetaApiLinkError:
        _delete_quiet(token, account_id)
        raise
    if live:
        created = {**created, **live}
    _persist(
        config_path,
        account_id=account_id,
        region=_region(created, region),
        login=account_login,
        server=str(created.get("server") or account_server),
    )
    return _status(config_path, live=created, locale=locale, connected=True)


def unlink_account(
    *,
    config_path: Path | None = None,
    locale: str | None = None,
) -> dict[str, Any]:
    """Remove the MetaAPI account and clear the saved id."""
    _reject_env_override(locale)
    stored = _load(config_path).trading_metaapi
    account_id = stored.account_id.strip()
    token = _token(config_path)
    if account_id and token:
        _delete(token, account_id, locale=locale)
    _persist(config_path, account_id="", login="", server="", region=stored.region or "new-york")
    return _status(config_path, live=None, locale=locale, connected=False)


def account_status(
    *,
    config_path: Path | None = None,
    locale: str | None = None,
) -> dict[str, Any]:
    """Saved link plus the live MetaAPI state when a token and id exist."""
    stored = _load(config_path).trading_metaapi
    live: dict[str, Any] | None = None
    token = _token(config_path)
    if token and stored.account_id.strip():
        try:
            live = _read(token, stored.account_id.strip())
        except MetaApiLinkError:
            live = None
    connected = bool(stored.account_id.strip() and token)
    return _status(config_path, live=live, locale=locale, connected=connected)


def _reject_env_override(locale: str | None) -> None:
    if (os.environ.get("METAAPI_ACCOUNT_ID") or "").strip():
        raise MetaApiLinkError(tr("metaapi.connect.env_override", locale=locale))


def _require_token(locale: str | None, config_path: Path | None) -> str:
    token = _token(config_path)
    if not token:
        raise MetaApiLinkError(tr("metaapi.connect.token_missing", locale=locale))
    return token


def _token(config_path: Path | None = None) -> str:
    env = (os.environ.get("METAAPI_TOKEN") or "").strip()
    if env:
        return env
    try:
        return _load(config_path).trading_metaapi.effective_token().strip()
    except (OSError, ValueError):
        return ""


def _stored_region(config_path: Path | None) -> str:
    region = _load(config_path).trading_metaapi.region.strip().lower()
    return region if region in REGIONS else "new-york"


def _load(config_path: Path | None):
    if config_path is None:
        return load_config()
    return load_config(config_path)


def _persist(
    config_path: Path | None,
    *,
    account_id: str,
    region: str,
    login: str,
    server: str,
) -> None:
    config = _load(config_path)
    meta = config.trading_metaapi
    meta.account_id = account_id
    meta.region = region if region in REGIONS else "new-york"
    meta.login = login
    meta.server = server
    save_config(config, config_path)


def _status(
    config_path: Path | None,
    *,
    live: dict[str, Any] | None,
    locale: str | None,
    connected: bool,
) -> dict[str, Any]:
    del locale
    stored = _load(config_path).trading_metaapi
    login = str((live or {}).get("login") or stored.login or "")
    server = str((live or {}).get("server") or stored.server or "")
    name = str((live or {}).get("name") or "")
    account = None
    if login or server or name:
        account = {
            "name": name,
            "login": login,
            "server": server,
            "balance": (live or {}).get("balance"),
            "currency": str((live or {}).get("currency") or ""),
        }
    return {
        "configured": bool(_token(config_path) and (stored.account_id or "").strip()),
        "connected": connected and bool((stored.account_id or "").strip()),
        "login": login,
        "server": server,
        "region": stored.region,
        "account": account,
    }


def _known_servers(query: str, token: str) -> list[dict[str, Any]]:
    data = _call("get", f"{_BASE}/known-mt-servers/5", token, params={"query": query})
    return [row for row in _rows(data) if isinstance(row, dict)]


def _provision(
    token: str,
    *,
    login: str,
    password: str,
    server: str,
    name: str,
    region: str,
    locale: str | None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "name": f"Mokli {name}"[:64],
        "type": "cloud-g2",
        "login": login,
        "password": password,
        "server": server,
        "platform": "mt5",
        "magic": _MAGIC,
        "reliability": "regular",
        "region": region,
    }
    try:
        return _call("post", f"{_BASE}/users/current/accounts", token, body=body)
    except MetaApiLinkError as exc:
        raise MetaApiLinkError(
            exc.message or tr("metaapi.connect.failed", locale=locale),
            status=exc.status,
        ) from exc


def _deploy(token: str, account_id: str, *, locale: str | None) -> None:
    try:
        _call("post", f"{_BASE}/users/current/accounts/{account_id}/deploy", token)
    except MetaApiLinkError as exc:
        raise MetaApiLinkError(
            exc.message or tr("metaapi.connect.failed", locale=locale),
            status=exc.status,
        ) from exc


def _read(token: str, account_id: str) -> dict[str, Any]:
    return _call("get", f"{_BASE}/users/current/accounts/{account_id}", token)


def _delete(token: str, account_id: str, *, locale: str | None) -> None:
    try:
        _call("delete", f"{_BASE}/users/current/accounts/{account_id}", token)
    except MetaApiLinkError as exc:
        if exc.status == 404:
            return
        raise MetaApiLinkError(
            exc.message or tr("metaapi.connect.failed", locale=locale),
            status=exc.status,
        ) from exc


def _delete_quiet(token: str, account_id: str) -> None:
    try:
        _delete(token, account_id, locale=None)
    except MetaApiLinkError:
        return


def _call(
    method: str,
    url: str,
    token: str,
    *,
    params: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    headers = {"auth-token": token, "Accept": "application/json"}
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            if method == "get":
                response = client.get(url, headers=headers, params=params)
            elif method == "post":
                response = client.post(url, headers=headers, json=body or {})
            elif method == "delete":
                response = client.delete(url, headers=headers)
            else:
                raise MetaApiLinkError(tr("metaapi.connect.failed"), status=500)
    except httpx.HTTPError as exc:
        raise MetaApiLinkError(tr("metaapi.connect.failed"), status=502) from exc
    if response.status_code not in {200, 201, 204}:
        raise MetaApiLinkError(_failure_text(response), status=_http_status(response.status_code))
    return _read_json(response)


def _http_status(code: int) -> int:
    if code in {400, 401, 403, 404, 409}:
        return code
    return 502


def _failure_text(response: httpx.Response) -> str:
    data = _read_json(response)
    for key in ("message", "error", "errmsg"):
        value = data.get(key)
        if isinstance(value, str) and value.strip() and "password" not in value.lower():
            return value.strip()[:300]
    return tr("metaapi.connect.failed")


def _read_json(response: httpx.Response) -> dict[str, Any]:
    if response.status_code == 204:
        return {}
    try:
        text = response.text
    except Exception:
        return {}
    if not text or not text.strip():
        return {}
    try:
        data = response.json()
    except Exception:
        return {}
    if isinstance(data, list):
        return {"results": data}
    return data if isinstance(data, dict) else {}


def _rows(data: dict[str, Any]) -> list[Any]:
    for key in ("results", "servers", "items"):
        value = data.get(key)
        if isinstance(value, list):
            return value
    return []


def _group(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[str]] = {}
    for row in rows:
        server = str(row.get("server") or row.get("name") or "").strip()
        company = str(row.get("company") or row.get("broker") or server).strip()
        if not server or not company:
            continue
        servers = grouped.setdefault(company, [])
        if server not in servers and len(servers) < _MAX_SERVERS:
            servers.append(server)
    companies: list[dict[str, Any]] = []
    for name, servers in grouped.items():
        if len(companies) >= _MAX_COMPANIES:
            break
        companies.append({"name": name, "label": name, "servers": servers})
    return companies


def _account_id(data: dict[str, Any]) -> str:
    for key in ("id", "_id", "accountId"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _region(data: dict[str, Any], fallback: str) -> str:
    value = data.get("region")
    if isinstance(value, str) and value.strip().lower() in REGIONS:
        return value.strip().lower()
    return fallback if fallback in REGIONS else "new-york"

