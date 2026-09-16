"""MetaAPI Cloud MT5 adapter — account snapshot plus order send after HITL confirm."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from nanobot.trading.config import TradingConfig, load_trading_config


class MetaApiTransport(Protocol):
    async def account_snapshot(self) -> dict[str, Any]: ...
    async def quote(self, symbol: str) -> dict[str, Any]: ...
    async def open_positions(self) -> list[dict[str, Any]]: ...
    async def open_orders(self) -> list[dict[str, Any]]: ...
    async def send_market(self, payload: dict[str, Any]) -> dict[str, Any]: ...
    async def modify_position(self, payload: dict[str, Any]) -> dict[str, Any]: ...
    async def close_position(self, payload: dict[str, Any]) -> dict[str, Any]: ...
    async def cancel_order(self, payload: dict[str, Any]) -> dict[str, Any]: ...


@dataclass
class NullTransport:
    """Used when the SDK extra is missing — never sends live orders."""

    reason: str = "metaapi-cloud-sdk is not installed"

    async def account_snapshot(self) -> dict[str, Any]:
        return {"ok": False, "error": self.reason}

    async def quote(self, symbol: str) -> dict[str, Any]:
        return {"ok": False, "symbol": symbol, "error": self.reason}

    async def open_positions(self) -> list[dict[str, Any]]:
        return []

    async def open_orders(self) -> list[dict[str, Any]]:
        return []

    async def send_market(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": False, "error": self.reason, "payload": payload}

    async def modify_position(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": False, "error": self.reason}

    async def close_position(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": False, "error": self.reason}

    async def cancel_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": False, "error": self.reason}


class SdkTransport:
    def __init__(self, config: TradingConfig) -> None:
        self.config = config
        self._api: Any = None
        self._account: Any = None

    async def _conn(self) -> Any:
        if self._account is not None:
            return self._account
        from metaapi_cloud_sdk import MetaApi

        self._api = MetaApi(self.config.metaapi_token)
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
        result = await rpc.create_market_buy_order(
            payload["symbol"],
            payload["lot"],
            payload.get("stop"),
            payload.get("take_profit"),
            {"comment": payload.get("comment") or ""},
        ) if payload["side"] == "buy" else await rpc.create_market_sell_order(
            payload["symbol"],
            payload["lot"],
            payload.get("stop"),
            payload.get("take_profit"),
            {"comment": payload.get("comment") or ""},
        )
        return {"ok": True, "result": result}

    async def modify_position(self, payload: dict[str, Any]) -> dict[str, Any]:
        rpc = await self._conn()
        result = await rpc.modify_position(
            payload["position_id"],
            payload.get("stop"),
            payload.get("take_profit"),
        )
        return {"ok": True, "result": result}

    async def close_position(self, payload: dict[str, Any]) -> dict[str, Any]:
        rpc = await self._conn()
        result = await rpc.close_position(payload["position_id"])
        return {"ok": True, "result": result}

    async def cancel_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        rpc = await self._conn()
        fn = getattr(rpc, "cancel_order", None)
        if fn is None:
            return {"ok": False, "error": "cancel_order is not available on this transport"}
        result = await fn(payload["order_id"])
        return {"ok": True, "result": result}


def build_transport(config: TradingConfig | None = None) -> MetaApiTransport:
    config = config or load_trading_config()
    if not config.metaapi_configured:
        return NullTransport("METAAPI_TOKEN / METAAPI_ACCOUNT_ID are not set")
    try:
        import metaapi_cloud_sdk  # noqa: F401
    except ImportError:
        return NullTransport("metaapi-cloud-sdk is not installed")
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
