"""Self-hosted MetaTrader 5 broker via the mt5linux RPyC bridge.

The terminal is expected to be running already. This module only dials
``MT5_HOST:MT5_PORT``. It does not start a container or call a cloud broker.
"""

from __future__ import annotations

import asyncio
import importlib.util
import logging
import os
import socket
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

from mokli.trading.broker_result import wrap_sdk_result
from mokli.trading.config import TradingConfig, load_trading_config
from mokli.trading.i18n import tr
from mokli.trading.policy import MAGIC_SWING

logger = logging.getLogger(__name__)

_DEFAULT_HOST = "localhost"
_DEFAULT_PORT = 8001
_DEFAULT_TIMEOUT = 10.0
_DEFAULT_DEVIATION = 20
_DEFAULT_ATTEMPTS = 3

_DEAL = 1
_PENDING = 5
_SLTP = 6
_REMOVE = 8
_BUY = 0
_SELL = 1
_BUY_LIMIT = 2
_SELL_LIMIT = 3
_BUY_STOP = 4
_SELL_STOP = 5
_GTC = 0
_FILLING_FOK = 0
_FILLING_IOC = 1
_FILLING_RETURN = 2
_POSITION_BUY = 0
_RETCODES = {
    10008: "TRADE_RETCODE_PLACED",
    10009: "TRADE_RETCODE_DONE",
    10010: "TRADE_RETCODE_DONE_PARTIAL",
}
_TIMEFRAMES = {
    "M1": 1,
    "1": 1,
    "M5": 5,
    "5": 5,
    "M15": 15,
    "15": 15,
    "M30": 30,
    "30": 30,
    "H1": 16385,
    "60": 16385,
    "H4": 16388,
    "240": 16388,
    "D1": 16408,
    "D": 16408,
    "W1": 32769,
    "MN1": 49153,
}
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

ClientFactory = Callable[[str, int], Any]


class Mt5ConnectionError(Exception):
    """The bridge or the terminal rejected a call. The message is already redacted."""


def redact_secret(text: str, secret: str | None) -> str:
    """Remove a credential if a broker exception echoed it."""
    if not secret:
        return text
    cleaned = text.replace(secret, "***")
    return cleaned


def sdk_available() -> bool:
    return importlib.util.find_spec("mt5linux") is not None


def public_account_information(info: Any) -> dict[str, Any]:
    """Operator-safe account snapshot — never includes a password."""
    if not isinstance(info, dict):
        return {}
    out: dict[str, Any] = {}
    for key in _PUBLIC_ACCOUNT_KEYS:
        if key in info and info[key] not in (None, ""):
            out[key] = info[key]
    return out


def _env_int(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("%s is not an integer; using %s", name, default)
        return default


def _env_float(name: str, default: float) -> float:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning("%s is not a number; using %s", name, default)
        return default


def _plain(value: Any) -> Any:
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return item()
        except Exception:
            return value
    return value


def _as_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    asdict = getattr(value, "_asdict", None)
    if callable(asdict):
        return {str(key): _plain(item) for key, item in asdict().items()}
    names = getattr(getattr(value, "dtype", None), "names", None)
    if names:
        return {str(name): _plain(value[name]) for name in names}
    data = getattr(value, "__dict__", None)
    if isinstance(data, dict) and data:
        return {
            str(key): _plain(item)
            for key, item in data.items()
            if not str(key).startswith("_")
        }
    return {}


def _field(value: Any, name: str, default: Any = None) -> Any:
    mapped = _as_mapping(value)
    if name in mapped:
        return mapped[name]
    if hasattr(value, name):
        return _plain(getattr(value, name))
    return default


def _last_error(client: Any, password: str) -> str:
    try:
        err = client.last_error()
    except Exception as exc:
        return redact_secret(str(exc), password)
    return redact_secret(str(err), password)


def _timeframe(name: str) -> int:
    key = str(name or "M1").strip().upper()
    return _TIMEFRAMES.get(key, _TIMEFRAMES["M1"])


def _rates(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    rows: list[dict[str, Any]] = []
    try:
        iterator = list(value)
    except TypeError:
        return []
    for bar in iterator:
        mapped = _as_mapping(bar)
        if mapped:
            rows.append(mapped)
    return rows


def _account_view(info: Any) -> dict[str, Any]:
    raw = _as_mapping(info)
    if not raw:
        return {}
    trade_allowed = raw.get("trade_allowed")
    return public_account_information(
        {
            "login": raw.get("login"),
            "name": raw.get("name"),
            "server": raw.get("server"),
            "broker": raw.get("company"),
            "company": raw.get("company"),
            "currency": raw.get("currency"),
            "balance": raw.get("balance"),
            "equity": raw.get("equity"),
            "margin": raw.get("margin"),
            "leverage": raw.get("leverage"),
            "tradeAllowed": trade_allowed,
            "trade_allowed": trade_allowed,
            "platform": "mt5",
        }
    )


def _symbol_public(row: Any) -> dict[str, Any] | None:
    name = str(_field(row, "name") or "").strip()
    if not name:
        return None
    trade_mode = _field(row, "trade_mode")
    try:
        mode = int(trade_mode) if trade_mode is not None else 4
    except (TypeError, ValueError):
        mode = 4
    if mode == 0:
        return None
    digits = _field(row, "digits")
    try:
        digits_n = int(digits) if digits is not None else None
    except (TypeError, ValueError):
        digits_n = None
    return {
        "name": name,
        "description": str(_field(row, "description") or ""),
        "digits": digits_n,
        "path": str(_field(row, "path") or ""),
        "trade_mode": mode,
    }


def _filter_symbols(rows: list[Any], *, query: str, limit: int) -> dict[str, Any]:
    needle = query.strip().casefold()
    public: list[dict[str, Any]] = []
    for row in rows:
        item = _symbol_public(row)
        if item is None:
            continue
        if needle:
            hay = " ".join(
                (item["name"], item["description"], item["path"])
            ).casefold()
            if needle not in hay:
                continue
        public.append(item)
    capped = max(1, min(int(limit), 800))
    return {
        "ok": True,
        "source": "mt5",
        "total": len(public),
        "symbols": public[:capped],
    }


def _position_row(row: Any) -> dict[str, Any]:
    raw = _as_mapping(row)
    ticket = raw.get("ticket")
    side = "buy" if int(raw.get("type") or 0) == _POSITION_BUY else "sell"
    stop = raw.get("sl")
    take = raw.get("tp")
    return {
        "id": str(ticket or ""),
        "ticket": str(ticket or ""),
        "positionId": str(ticket or ""),
        "symbol": raw.get("symbol") or "",
        "type": side,
        "volume": raw.get("volume"),
        "openPrice": raw.get("price_open"),
        "stopLoss": None if not stop else stop,
        "takeProfit": None if not take else take,
        "time": raw.get("time"),
        "profit": raw.get("profit"),
        "comment": raw.get("comment") or "",
    }


def _order_row(row: Any) -> dict[str, Any]:
    raw = _as_mapping(row)
    ticket = raw.get("ticket")
    return {
        "id": str(ticket or ""),
        "ticket": str(ticket or ""),
        "orderId": str(ticket or ""),
        "symbol": raw.get("symbol") or "",
        "type": raw.get("type"),
        "volume": raw.get("volume_current", raw.get("volume")),
        "price": raw.get("price_open"),
        "time": raw.get("time_setup", raw.get("time")),
    }


def _send_result(result: Any, password: str) -> dict[str, Any]:
    raw = _as_mapping(result)
    if not raw:
        return {"ok": False, "error": tr("mt5.empty_broker_result"), "result": None}
    try:
        retcode = int(raw.get("retcode") or 0)
    except (TypeError, ValueError):
        retcode = 0
    deal = raw.get("deal") or 0
    order = raw.get("order") or 0
    try:
        ticket = int(deal or 0) or int(order or 0)
    except (TypeError, ValueError):
        ticket = 0
    comment = redact_secret(str(raw.get("comment") or ""), password)
    body = {
        "numericCode": retcode,
        "stringCode": _RETCODES.get(retcode, f"TRADE_RETCODE_{retcode}"),
        "positionId": str(ticket) if ticket else "",
        "orderId": str(order) if order else "",
        "comment": comment,
    }
    return wrap_sdk_result(body)


def _filling(client: Any, symbol: str) -> int:
    info = client.symbol_info(symbol)
    try:
        mode = int(_field(info, "filling_mode") or 0)
    except (TypeError, ValueError):
        mode = 0
    if mode & 2:
        return _FILLING_IOC
    if mode & 1:
        return _FILLING_FOK
    return _FILLING_RETURN


def _deviation() -> int:
    value = _env_int("MT5_DEVIATION", _DEFAULT_DEVIATION)
    return value if value >= 0 else _DEFAULT_DEVIATION


def _comment(text: str) -> str:
    cleaned = "".join(ch for ch in str(text or "") if ch.isalnum() or ch in " _-.")
    return cleaned[:31]


def _terminal_path() -> str:
    return os.environ.get("MT5_TERMINAL_PATH", "").strip()


def _portable_terminal() -> bool:
    return os.environ.get("MT5_PORTABLE", "").strip().lower() in {"1", "true", "yes"}


def _ipc_timeout_ms() -> int:
    raw = os.environ.get("MT5_IPC_TIMEOUT_MS", "").strip()
    if not raw:
        return 45_000
    try:
        return max(1000, int(raw))
    except ValueError:
        return 45_000


def _open_kwargs(timeout_ms: int) -> dict[str, Any]:
    init_kwargs: dict[str, Any] = {"timeout": max(1000, int(timeout_ms))}
    terminal = _terminal_path()
    if terminal:
        init_kwargs["path"] = terminal
    if _portable_terminal():
        init_kwargs["portable"] = True
    return init_kwargs


def read_terminal_account_sync(
    *,
    host: str,
    port: int,
    ipc_timeout_ms: int = 8_000,
    client_factory: ClientFactory | None = None,
) -> dict[str, Any] | None:
    """Read the account already open in the terminal window.

    Returns ``None`` when the terminal has not logged in. This does not send
    a password.
    """
    if client_factory is not None:
        client = client_factory(host, port)
    else:
        from mt5linux import MetaTrader5

        client = MetaTrader5(host=host, port=int(port))
    try:
        if client.initialize(**_open_kwargs(ipc_timeout_ms)) is False:
            return None
        view = _account_view(client.account_info())
    except Exception:
        logger.debug("MT5 terminal window has no account host=%s port=%s", host, port)
        return None
    finally:
        shutdown = getattr(client, "shutdown", None)
        if callable(shutdown):
            try:
                shutdown()
            except Exception:
                logger.debug("MT5 shutdown after account read failed")
    login = str(view.get("login") or "")
    server = str(view.get("server") or "")
    if not login or login == "0" or not server:
        return None
    return view


async def read_terminal_account(**kwargs: Any) -> dict[str, Any] | None:
    return await asyncio.to_thread(read_terminal_account_sync, **kwargs)


class Mt5LinuxBroker:
    """``mt5linux.MetaTrader5`` client. Every dial target comes from config or env."""

    def __init__(
        self,
        *,
        host: str | None,
        port: int | None,
        login: str | None,
        password: str | None,
        server: str | None,
        access: str | None = None,
        attempts: int = _DEFAULT_ATTEMPTS,
        retry_delay: float = 0.4,
        timeout: float | None = None,
        ipc_timeout_ms: int | None = None,
        client_factory: ClientFactory | None = None,
    ) -> None:
        self.host = (host or "").strip() or _DEFAULT_HOST
        self.port = int(port or _DEFAULT_PORT)
        self.login = (login or "").strip()
        self.password = password or ""
        self.server = (server or "").strip()
        # Broker access address (host:port). The terminal reaches a company it
        # has never opened only when initialize() is given this address.
        self.access = (access or "").strip()
        self.attempts = max(1, int(attempts))
        self.retry_delay = max(0.0, float(retry_delay))
        self.timeout = _DEFAULT_TIMEOUT if timeout is None else max(1.0, float(timeout))
        self.ipc_timeout_ms = None if ipc_timeout_ms is None else max(1000, int(ipc_timeout_ms))
        self._factory = client_factory
        self._client: Any = None
        self._lock = threading.Lock()

    def __repr__(self) -> str:
        return (
            f"Mt5LinuxBroker(host={self.host!r}, port={self.port!r}, "
            f"login={self.login!r}, server={self.server!r})"
        )

    @classmethod
    def from_config(cls, config: TradingConfig, **kwargs: Any) -> Mt5LinuxBroker:
        return cls(
            host=config.mt5_host,
            port=config.mt5_port,
            login=config.mt5_login,
            password=config.mt5_password,
            server=config.mt5_server,
            access=config.mt5_access,
            timeout=kwargs.pop("timeout", _env_float("MT5_TIMEOUT", _DEFAULT_TIMEOUT)),
            **kwargs,
        )

    @classmethod
    def from_env(cls, **kwargs: Any) -> Mt5LinuxBroker:
        return cls.from_config(load_trading_config(), **kwargs)

    def _open(self) -> Any:
        if self._factory is not None:
            return self._factory(self.host, self.port)
        self._probe()
        from mt5linux import MetaTrader5

        return MetaTrader5(host=self.host, port=int(self.port))

    def _probe(self) -> None:
        try:
            with socket.create_connection((self.host, int(self.port)), timeout=self.timeout):
                return
        except OSError as exc:
            raise Mt5ConnectionError(redact_secret(str(exc), self.password)) from exc

    def _drop_locked(self) -> None:
        client = self._client
        self._client = None
        if client is None:
            return
        shutdown = getattr(client, "shutdown", None)
        if not callable(shutdown):
            return
        try:
            shutdown()
        except Exception:
            logger.debug("MT5 shutdown failed host=%s port=%s", self.host, self.port)

    def _terminal_kwargs(self, *, with_credentials: bool) -> dict[str, Any]:
        timeout_ms = self.ipc_timeout_ms if self.ipc_timeout_ms is not None else _ipc_timeout_ms()
        init_kwargs = _open_kwargs(timeout_ms)
        if with_credentials:
            init_kwargs["login"] = int(self.login)
            init_kwargs["password"] = self.password
            init_kwargs["server"] = self._dial_server()
        return init_kwargs

    def _dial_server(self) -> str:
        return self.access or self.server

    def _session(self, client: Any) -> None:
        if self.password:
            if not self.login or not self.server:
                raise Mt5ConnectionError(tr("mt5.credentials_missing"))
            try:
                int(self.login)
            except ValueError:
                raise Mt5ConnectionError(tr("mt5.connect.login_invalid")) from None
            # A server name the terminal has never opened stalls on IPC.
            # The company directory's access address reaches the broker directly.
            init_kwargs = self._terminal_kwargs(with_credentials=True)
            if client.initialize(**init_kwargs) is False:
                raise Mt5ConnectionError(_last_error(client, self.password))
            logged = client.login(
                int(self.login),
                password=self.password,
                server=self._dial_server(),
            )
            if logged is False:
                raise Mt5ConnectionError(_last_error(client, self.password))
            return
        if not self.login or not self.server:
            raise Mt5ConnectionError(tr("mt5.credentials_missing"))
        # The operator already logged in inside the terminal window.
        if client.initialize(**self._terminal_kwargs(with_credentials=False)) is False:
            raise Mt5ConnectionError(_last_error(client, ""))
        seen = str(_account_view(client.account_info()).get("login") or "")
        if seen != self.login:
            raise Mt5ConnectionError(tr("mt5.credentials_missing"))

    def _attempt(self, fn: Callable[[Any], Any] | None = None) -> Any:
        last = tr("mt5.connect.failed")
        for attempt in range(1, self.attempts + 1):
            with self._lock:
                try:
                    if self._client is None:
                        self._client = self._open()
                        self._session(self._client)
                    if fn is None:
                        return {"ok": True, "host": self.host, "port": self.port}
                    return fn(self._client)
                except Exception as exc:
                    self._drop_locked()
                    last = redact_secret(str(exc), self.password)
                    logger.warning(
                        "MT5 call failed host=%s port=%s attempt=%s/%s error=%s",
                        self.host,
                        self.port,
                        attempt,
                        self.attempts,
                        last,
                    )
            if attempt < self.attempts and self.retry_delay > 0:
                time.sleep(self.retry_delay * attempt)
        if fn is None:
            return {"ok": False, "error": last}
        raise Mt5ConnectionError(last)

    async def connect(self) -> dict[str, Any]:
        def _fresh() -> dict[str, Any]:
            with self._lock:
                self._drop_locked()
            result = self._attempt(None)
            return result if isinstance(result, dict) else {"ok": False, "error": tr("mt5.connect.failed")}

        return await asyncio.to_thread(_fresh)

    async def get_account_info(self) -> dict[str, Any]:
        def _read(client: Any) -> dict[str, Any]:
            info = _account_view(client.account_info())
            if not info:
                return {"ok": False, "error": tr("mt5.empty_broker_result")}
            return {"ok": True, "account": info}

        try:
            return await asyncio.to_thread(self._attempt, _read)
        except Mt5ConnectionError as exc:
            return {"ok": False, "error": str(exc)}

    async def get_symbol_price(self, symbol: str) -> dict[str, Any]:
        def _read(client: Any) -> dict[str, Any]:
            client.symbol_select(symbol, True)
            tick = client.symbol_info_tick(symbol)
            bid = _field(tick, "bid")
            ask = _field(tick, "ask")
            if bid is None or ask is None:
                return {"ok": False, "symbol": symbol, "error": tr("mt5.empty_broker_result")}
            spread = None
            try:
                spread = float(ask) - float(bid)
            except (TypeError, ValueError):
                spread = None
            return {
                "ok": True,
                "symbol": symbol,
                "bid": bid,
                "ask": ask,
                "spread": spread,
                "time": _field(tick, "time"),
                "time_msc": _field(tick, "time_msc"),
            }

        try:
            return await asyncio.to_thread(self._attempt, _read)
        except Mt5ConnectionError as exc:
            return {"ok": False, "symbol": symbol, "error": str(exc)}

    async def list_symbols(self, query: str = "", limit: int = 200) -> dict[str, Any]:
        """Tradable symbols on the connected terminal. Disabled symbols are omitted."""

        def _read(client: Any) -> dict[str, Any]:
            raw = client.symbols_get()
            return {"ok": True, "symbols": list(raw or [])}

        try:
            payload = await asyncio.to_thread(self._attempt, _read)
        except Mt5ConnectionError as exc:
            return {"ok": False, "error": str(exc), "symbols": []}
        if not isinstance(payload, dict) or not payload.get("ok"):
            return {"ok": False, "symbols": [], "error": (payload or {}).get("error")}
        return _filter_symbols(payload.get("symbols") or [], query=query, limit=limit)

    async def get_candles(self, symbol: str, timeframe: str, count: int) -> list[dict[str, Any]]:
        def _read(client: Any) -> list[dict[str, Any]]:
            client.symbol_select(symbol, True)
            rates = client.copy_rates_from_pos(symbol, _timeframe(timeframe), 0, int(count))
            return _rates(rates)

        try:
            return await asyncio.to_thread(self._attempt, _read)
        except Mt5ConnectionError:
            logger.warning("MT5 candles failed host=%s port=%s symbol=%s", self.host, self.port, symbol)
            return []

    async def place_order(
        self,
        *,
        symbol: str,
        side: str,
        lot: float,
        stop: float | None = None,
        take_profit: float | None = None,
        comment: str = "",
        kind: str = "market",
        price: float | None = None,
    ) -> dict[str, Any]:
        def _send(client: Any) -> dict[str, Any]:
            return _send_result(
                client.order_send(
                    _order_request(
                        client,
                        symbol=symbol,
                        side=side,
                        lot=lot,
                        stop=stop,
                        take_profit=take_profit,
                        comment=comment,
                        kind=kind,
                        price=price,
                    )
                ),
                self.password,
            )

        try:
            return await asyncio.to_thread(self._attempt, _send)
        except Mt5ConnectionError as exc:
            return {"ok": False, "error": str(exc)}

    async def close_order(
        self,
        *,
        position_id: str | None = None,
        order_id: str | None = None,
        volume: float | None = None,
    ) -> dict[str, Any]:
        def _send(client: Any) -> dict[str, Any]:
            if order_id:
                request = {"action": _REMOVE, "order": int(order_id)}
                return _send_result(client.order_send(request), self.password)
            if not position_id:
                return {"ok": False, "error": tr("mt5.broker_rejected")}
            return _send_result(
                client.order_send(_close_request(client, position_id, volume)),
                self.password,
            )

        try:
            return await asyncio.to_thread(self._attempt, _send)
        except Mt5ConnectionError as exc:
            return {"ok": False, "error": str(exc)}
        except (TypeError, ValueError) as exc:
            return {"ok": False, "error": redact_secret(str(exc), self.password)}

    async def get_open_positions(self) -> list[dict[str, Any]]:
        def _read(client: Any) -> list[dict[str, Any]]:
            rows = client.positions_get()
            return [_position_row(row) for row in list(rows or [])]

        try:
            return await asyncio.to_thread(self._attempt, _read)
        except Mt5ConnectionError:
            logger.warning("MT5 positions failed host=%s port=%s", self.host, self.port)
            return []

    async def get_open_orders(self) -> list[dict[str, Any]]:
        def _read(client: Any) -> list[dict[str, Any]]:
            getter = getattr(client, "orders_get", None)
            if getter is None:
                return []
            rows = getter()
            return [_order_row(row) for row in list(rows or [])]

        try:
            return await asyncio.to_thread(self._attempt, _read)
        except Mt5ConnectionError:
            logger.warning("MT5 orders failed host=%s port=%s", self.host, self.port)
            return []

    async def modify_position(
        self,
        *,
        position_id: str,
        stop: float | None = None,
        take_profit: float | None = None,
    ) -> dict[str, Any]:
        def _send(client: Any) -> dict[str, Any]:
            position = _find_position(client, position_id)
            if position is None:
                return {"ok": False, "error": tr("mt5.broker_rejected")}
            request = {
                "action": _SLTP,
                "position": int(position_id),
                "symbol": _field(position, "symbol"),
                "sl": float(stop if stop is not None else (_field(position, "sl") or 0)),
                "tp": float(
                    take_profit if take_profit is not None else (_field(position, "tp") or 0)
                ),
            }
            return _send_result(client.order_send(request), self.password)

        try:
            return await asyncio.to_thread(self._attempt, _send)
        except Mt5ConnectionError as exc:
            return {"ok": False, "error": str(exc)}


def _find_position(client: Any, position_id: str) -> Any:
    rows = client.positions_get() or []
    for row in rows:
        if str(_field(row, "ticket") or "") == str(position_id):
            return row
    return None


def _tick_price(client: Any, symbol: str, *, buy: bool) -> float:
    client.symbol_select(symbol, True)
    tick = client.symbol_info_tick(symbol)
    raw = _field(tick, "ask" if buy else "bid")
    return float(raw or 0)


def _order_request(
    client: Any,
    *,
    symbol: str,
    side: str,
    lot: float,
    stop: float | None,
    take_profit: float | None,
    comment: str,
    kind: str,
    price: float | None,
) -> dict[str, Any]:
    buy = str(side).lower() != "sell"
    pending = str(kind or "market").lower()
    if pending in {"", "market"}:
        order_type = _BUY if buy else _SELL
        action = _DEAL
        order_price = _tick_price(client, symbol, buy=buy)
    else:
        action = _PENDING
        if pending == "stop":
            order_type = _BUY_STOP if buy else _SELL_STOP
        else:
            order_type = _BUY_LIMIT if buy else _SELL_LIMIT
        order_price = float(price or 0)
    return {
        "action": action,
        "symbol": symbol,
        "volume": float(lot),
        "type": order_type,
        "price": order_price,
        "sl": float(stop or 0),
        "tp": float(take_profit or 0),
        "deviation": _deviation(),
        "magic": MAGIC_SWING,
        "comment": _comment(comment),
        "type_time": _GTC,
        "type_filling": _filling(client, symbol),
    }


def _close_request(client: Any, position_id: str, volume: float | None) -> dict[str, Any]:
    position = _find_position(client, position_id)
    if position is None:
        raise Mt5ConnectionError(tr("mt5.broker_rejected"))
    symbol = str(_field(position, "symbol") or "")
    buy = int(_field(position, "type") or 0) == _POSITION_BUY
    current = float(_field(position, "volume") or 0)
    close_volume = float(volume) if volume is not None else current
    return {
        "action": _DEAL,
        "position": int(position_id),
        "symbol": symbol,
        "volume": close_volume,
        "type": _SELL if buy else _BUY,
        "price": _tick_price(client, symbol, buy=not buy),
        "deviation": _deviation(),
        "magic": MAGIC_SWING,
        "comment": "close",
        "type_time": _GTC,
        "type_filling": _filling(client, symbol),
    }


class BrokerTransport:
    """Adapts ``Mt5LinuxBroker`` to the verbs execution and management already call."""

    def __init__(self, broker: Mt5LinuxBroker, config: TradingConfig) -> None:
        self.broker = broker
        self.config = config

    async def account_snapshot(self) -> dict[str, Any]:
        return await self.broker.get_account_info()

    async def quote(self, symbol: str) -> dict[str, Any]:
        price = await self.broker.get_symbol_price(symbol)
        if not price.get("ok"):
            return price
        return {"ok": True, "quote": price}

    async def list_symbols(self, query: str = "", limit: int = 200) -> dict[str, Any]:
        return await self.broker.list_symbols(query, limit)

    async def candles(self, symbol: str, timeframe: str, count: int) -> list[dict[str, Any]]:
        return await self.broker.get_candles(symbol, timeframe, count)

    async def open_positions(self) -> list[dict[str, Any]]:
        return await self.broker.get_open_positions()

    async def open_orders(self) -> list[dict[str, Any]]:
        return await self.broker.get_open_orders()

    async def send_market(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.broker.place_order(
            symbol=str(payload["symbol"]),
            side=str(payload["side"]),
            lot=float(payload["lot"]),
            stop=payload.get("stop"),
            take_profit=payload.get("take_profit"),
            comment=str(payload.get("comment") or ""),
            kind="market",
        )

    async def send_pending(self, payload: dict[str, Any]) -> dict[str, Any]:
        kind = str(payload.get("kind") or "limit")
        if kind not in {"limit", "stop"}:
            kind = "limit"
        return await self.broker.place_order(
            symbol=str(payload["symbol"]),
            side=str(payload["side"]),
            lot=float(payload["lot"]),
            stop=payload.get("stop"),
            take_profit=payload.get("take_profit"),
            comment=str(payload.get("comment") or ""),
            kind=kind,
            price=payload.get("price"),
        )

    async def modify_position(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.broker.modify_position(
            position_id=str(payload["position_id"]),
            stop=payload.get("stop"),
            take_profit=payload.get("take_profit"),
        )

    async def close_position(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.broker.close_order(position_id=str(payload["position_id"]))

    async def close_partial(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.broker.close_order(
            position_id=str(payload["position_id"]),
            volume=payload.get("volume"),
        )

    async def cancel_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.broker.close_order(order_id=str(payload["order_id"]))


@dataclass
class NullTransport:
    """Used when mt5linux or the login is missing — never sends live orders."""

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

    async def list_symbols(self, query: str = "", limit: int = 200) -> dict[str, Any]:
        del query, limit
        return {
            "ok": False,
            "symbols": [],
            "total": 0,
            "error": self.reason,
            "reason_key": self.reason_key,
        }

    async def candles(self, symbol: str, timeframe: str, count: int) -> list[dict[str, Any]]:
        del symbol, timeframe, count
        return []

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

    async def send_pending(self, payload: dict[str, Any]) -> dict[str, Any]:
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

    async def close_partial(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": False, "error": self.reason, "reason_key": self.reason_key}

    async def cancel_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": False, "error": self.reason, "reason_key": self.reason_key}


def build_transport(config: TradingConfig | None = None) -> BrokerTransport | NullTransport:
    config = config or load_trading_config()
    if not config.mt5_configured:
        return NullTransport("mt5.credentials_missing")
    if not sdk_available():
        return NullTransport("mt5.sdk_missing")
    return BrokerTransport(Mt5LinuxBroker.from_config(config), config)


_TRANSPORT: BrokerTransport | NullTransport | None = None


def get_transport() -> BrokerTransport | NullTransport:
    global _TRANSPORT
    if _TRANSPORT is None:
        _TRANSPORT = build_transport()
    return _TRANSPORT


def set_transport_for_tests(transport: Any | None) -> None:
    global _TRANSPORT
    _TRANSPORT = transport


def reset_transport() -> None:
    """Drop the cached transport so the next get_transport() rebuilds from Config."""
    global _TRANSPORT
    _TRANSPORT = None
