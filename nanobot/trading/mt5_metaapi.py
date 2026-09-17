"""MetaAPI Cloud MT5 adapter — account snapshot plus order send after HITL confirm."""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from typing import Any, Protocol

from nanobot.trading.broker_result import wrap_sdk_result
from nanobot.trading.config import TradingConfig, load_trading_config
from nanobot.trading.i18n import tr
from nanobot.trading.policy import MAGIC_SWING

METAAPI_REGIONS = ("new-york", "london", "singapore", "amsterdam")
_PUBLIC_ACCOUNT_KEYS = (
    "login",
    "name",
    "server",
    "broker",
    "company",
    "currency",
    "balance",
    "equity",
    "margin",
    "leverage",
    "tradeAllowed",
    "trade_allowed",
    "platform",
)


class MetaApiTransport(Protocol):
    async def account_snapshot(self) -> dict[str, Any]: ...
    async def quote(self, symbol: str) -> dict[str, Any]: ...
    async def open_positions(self) -> list[dict[str, Any]]: ...
    async def open_orders(self) -> list[dict[str, Any]]: ...
    async def send_market(self, payload: dict[str, Any]) -> dict[str, Any]: ...
    async def modify_position(self, payload: dict[str, Any]) -> dict[str, Any]: ...
    async def close_position(self, payload: dict[str, Any]) -> dict[str, Any]: ...
    async def cancel_order(self, payload: dict[str, Any]) -> dict[str, Any]: ...


def _sdk_available() -> bool:
    return importlib.util.find_spec("metaapi_cloud_sdk") is not None


def sdk_available() -> bool:
    return _sdk_available()


@dataclass
class NullTransport:
    """Used when the SDK extra or credentials are missing — never sends live orders."""

    reason_key: str = "mt5.sdk_missing"

    @property
    def reason(self) -> str:
        return tr(self.reason_key)

    async def account_snapshot(self) -> dict[str, Any]:
        return {"ok": False, "error": self.reason, "reason_key": self.reason_key}

    async def quote(self, symbol: str) -> dict[str, Any]:
        return {
            "ok": False,
            "symbol": symbol,
            "error": self.reason,
            "reason_key": self.reason_key,
        }

    async def open_positions(self) -> list[dict[str, Any]]:
        return []

    async def open_orders(self) -> list[dict[str, Any]]:
        return []

    async def send_market(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "ok": False,
            "error": self.reason,
            "reason_key": self.reason_key,
            "payload": payload,
        }

    async def modify_position(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": False, "error": self.reason, "reason_key": self.reason_key}

    async def close_position(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": False, "error": self.reason, "reason_key": self.reason_key}

    async def cancel_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": False, "error": self.reason, "reason_key": self.reason_key}


class SdkTransport:
    def __init__(self, config: TradingConfig) -> None:
        self.config = config
        self._api: Any = None
        self._account: Any = None

    async def _conn(self) -> Any:
        if self._account is not None:
            return self._account
        from metaapi_cloud_sdk import MetaApi

        # Region selects the MetaAPI endpoint (new-york, london, singapore, …).
        opts: dict[str, Any] = {}
        if self.config.metaapi_region:
            opts["region"] = self.config.metaapi_region
        self._api = MetaApi(self.config.metaapi_token, **opts) if opts else MetaApi(
            self.config.metaapi_token
        )
        acc = await self._api.metatrader_account_api.get_account(self.config.metaapi_account_id)
        rpc = acc.get_rpc_connection()
        await rpc.connect()
        await rpc.wait_synchronized()
        self._account = rpc
        return rpc

    async def account_snapshot(self) -> dict[str, Any]:
        rpc = await self._conn()
        info = await rpc.get_account_information()
        return {"ok": True, "account": info}

    async def quote(self, symbol: str) -> dict[str, Any]:
        rpc = await self._conn()
        price = await rpc.get_symbol_price(symbol)
        return {"ok": True, "quote": price}

    async def open_positions(self) -> list[dict[str, Any]]:
        rpc = await self._conn()
        positions = await rpc.get_positions()
        return list(positions or [])

    async def open_orders(self) -> list[dict[str, Any]]:
        rpc = await self._conn()
        getter = getattr(rpc, "get_orders", None)
        if getter is None:
            return []
        orders = await getter()
        return list(orders or [])

    async def send_market(self, payload: dict[str, Any]) -> dict[str, Any]:
        rpc = await self._conn()
        options = {"comment": payload.get("comment") or ""}
        if payload["side"] == "buy":
            result = await rpc.create_market_buy_order(
                payload["symbol"],
                payload["lot"],
                payload.get("stop"),
                payload.get("take_profit"),
                options,
            )
        else:
            result = await rpc.create_market_sell_order(
                payload["symbol"],
                payload["lot"],
                payload.get("stop"),
                payload.get("take_profit"),
                options,
            )
        return wrap_sdk_result(result)

    async def modify_position(self, payload: dict[str, Any]) -> dict[str, Any]:
        rpc = await self._conn()
        result = await rpc.modify_position(
            payload["position_id"],
            payload.get("stop"),
            payload.get("take_profit"),
        )
        return wrap_sdk_result(result)

    async def close_position(self, payload: dict[str, Any]) -> dict[str, Any]:
        rpc = await self._conn()
        result = await rpc.close_position(payload["position_id"])
        return wrap_sdk_result(result)

    async def cancel_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        rpc = await self._conn()
        fn = getattr(rpc, "cancel_order", None)
        if fn is None:
            return {
                "ok": False,
                "error": tr("mt5.cancel_unsupported"),
                "reason_key": "mt5.cancel_unsupported",
            }
        result = await fn(payload["order_id"])
        return wrap_sdk_result(result)


def public_account_information(info: Any) -> dict[str, Any]:
    """Operator-safe account snapshot — never includes token or passwords."""
    if not isinstance(info, dict):
        return {}
    out: dict[str, Any] = {}
    for key in _PUBLIC_ACCOUNT_KEYS:
        if key in info and info[key] not in (None, ""):
            out[key] = info[key]
    return out


def _account_field(account: Any, name: str) -> Any:
    if isinstance(account, dict):
        return account.get(name)
    return getattr(account, name, None)


async def provision_mt5_account(
    *,
    token: str,
    region: str,
    login: str,
    password: str,
    server: str,
    name: str = "Lonora Gold",
) -> dict[str, Any]:
    """Create or reuse a MetaAPI MT5 account. Does not persist the MT5 password."""
    if not _sdk_available():
        return {
            "ok": False,
            "reason_key": "mt5.sdk_missing",
            "error": tr("mt5.sdk_missing"),
        }
    from metaapi_cloud_sdk import MetaApi

    opts: dict[str, Any] = {}
    if region:
        opts["region"] = region
    api = MetaApi(token, **opts) if opts else MetaApi(token)
    account_api = api.metatrader_account_api
    listing = getattr(account_api, "get_accounts_with_infinite_scroll_pagination", None)
    if listing is None:
        listing = account_api.get_accounts
    accounts = await listing()
    existing = None
    for row in accounts or []:
        same_login = str(_account_field(row, "login") or "") == login
        same_server = str(_account_field(row, "server") or "") == server
        if same_login and same_server:
            existing = row
            break
    account_id = ""
    try:
        if existing is None:
            create = account_api.create_account
            existing = await create(
                {
                    "name": name,
                    "type": "cloud-g2",
                    "login": login,
                    "password": password,
                    "server": server,
                    "platform": "mt5",
                    "magic": MAGIC_SWING,
                }
            )
        account_id = str(_account_field(existing, "id") or "")
        deploy = getattr(existing, "deploy", None)
        if callable(deploy):
            await deploy()
        wait = getattr(existing, "wait_deployed", None)
        if callable(wait):
            await wait(timeout_in_seconds=120)
    except Exception as exc:
        return {
            "ok": False,
            "reason_key": "mt5.connect.provision_failed",
            "error": tr("mt5.connect.provision_failed", detail=str(exc)),
        }
    if not account_id:
        return {
            "ok": False,
            "reason_key": "mt5.connect.provision_failed",
            "error": tr("mt5.connect.provision_failed", detail="missing account id"),
        }
    return {"ok": True, "account_id": account_id}


def build_transport(config: TradingConfig | None = None) -> MetaApiTransport:
    config = config or load_trading_config()
    if not config.metaapi_configured:
        return NullTransport("mt5.credentials_missing")
    if not _sdk_available():
        return NullTransport("mt5.sdk_missing")
    return SdkTransport(config)


_TRANSPORT: MetaApiTransport | None = None


def get_transport() -> MetaApiTransport:
    global _TRANSPORT
    if _TRANSPORT is None:
        _TRANSPORT = build_transport()
    return _TRANSPORT


def set_transport_for_tests(transport: MetaApiTransport | None) -> None:
    global _TRANSPORT
    _TRANSPORT = transport


def reset_transport() -> None:
    """Drop the cached transport so the next get_transport() rebuilds from Config."""
    global _TRANSPORT
    _TRANSPORT = None
