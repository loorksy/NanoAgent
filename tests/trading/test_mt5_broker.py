"""mt5linux broker adapter with an injected client — no network."""

from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

from mokli.trading.mt5_broker import Mt5ConnectionError, Mt5LinuxBroker, redact_secret


class FakeMt5:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.initialized = False
        self.requests: list[dict] = []
        self.login_calls: list[tuple] = []

    def initialize(self, **kwargs) -> bool:
        self.initialized = True
        self.init_kwargs = kwargs
        return True

    def login(self, login, password="", server="") -> bool:
        self.login_calls.append((login, password, server))
        return password != "bad"

    def last_error(self):
        return (1, "auth failed")

    def shutdown(self) -> None:
        self.initialized = False

    def account_info(self):
        return SimpleNamespace(
            login=10001,
            name="Desk",
            server="Broker-Demo",
            company="Broker",
            currency="USD",
            balance=2500.5,
            equity=2500.5,
            margin=0,
            margin_level=0,
            leverage=100,
            trade_allowed=True,
        )

    def symbol_select(self, symbol, enable) -> bool:
        return True

    def symbol_info(self, symbol):
        return SimpleNamespace(filling_mode=2)

    def symbol_info_tick(self, symbol):
        return SimpleNamespace(bid=2300.1, ask=2300.4, time=1_700_000_000)

    def copy_rates_from_pos(self, symbol, timeframe, start, count):
        return [{"time": 1, "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "tick_volume": 3}]

    def positions_get(self):
        return [
            SimpleNamespace(
                ticket=55,
                symbol="XAUUSD",
                type=0,
                volume=0.1,
                price_open=2300.0,
                sl=2290.0,
                tp=2320.0,
                time=1_700_000_000,
                profit=1.0,
                comment="",
            )
        ]

    def orders_get(self):
        return []

    def order_send(self, request):
        self.requests.append(dict(request))
        return SimpleNamespace(retcode=10009, deal=77, order=88, comment="done")


def _broker(**kwargs) -> tuple[Mt5LinuxBroker, list[FakeMt5]]:
    created: list[FakeMt5] = []

    def factory(host: str, port: int) -> FakeMt5:
        client = FakeMt5(host, port)
        created.append(client)
        return client

    broker = Mt5LinuxBroker(
        host=kwargs.get("host", "mt5.internal"),
        port=kwargs.get("port", 8001),
        login=kwargs.get("login", "10001"),
        password=kwargs.get("password", "s3cret-pass"),
        server=kwargs.get("server", "Broker-Demo"),
        attempts=kwargs.get("attempts", 3),
        retry_delay=0,
        ipc_timeout_ms=kwargs.get("ipc_timeout_ms"),
        client_factory=factory,
    )
    return broker, created


@pytest.mark.asyncio
async def test_connect_reads_host_port_and_hides_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MT5_TERMINAL_PATH", r"C:\MT5\terminal64.exe")
    monkeypatch.setenv("MT5_PORTABLE", "1")
    monkeypatch.setenv("MT5_IPC_TIMEOUT_MS", "8000")
    broker, created = _broker()
    result = await broker.connect()
    assert result == {"ok": True, "host": "mt5.internal", "port": 8001}
    assert created[0].init_kwargs == {
        "login": 10001,
        "password": "s3cret-pass",
        "server": "Broker-Demo",
        "timeout": 8000,
        "path": r"C:\MT5\terminal64.exe",
        "portable": True,
    }
    assert created[0].login_calls == [(10001, "s3cret-pass", "Broker-Demo")]
    assert "s3cret-pass" not in repr(broker)
    info = await broker.get_account_info()
    assert info["account"]["balance"] == 2500.5
    assert info["account"]["name"] == "Desk"
    price = await broker.get_symbol_price("XAUUSD")
    assert price["bid"] == 2300.1
    assert price["ask"] == 2300.4


@pytest.mark.asyncio
async def test_window_login_attaches_without_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MT5_TERMINAL_PATH", r"C:\MT5\terminal64.exe")
    monkeypatch.setenv("MT5_PORTABLE", "1")
    broker, created = _broker(password="", ipc_timeout_ms=8000)
    result = await broker.connect()
    assert result["ok"] is True
    assert "password" not in created[0].init_kwargs
    assert "login" not in created[0].init_kwargs
    assert created[0].init_kwargs["path"] == r"C:\MT5\terminal64.exe"
    assert created[0].init_kwargs["portable"] is True
    assert created[0].init_kwargs["timeout"] == 8000
    assert created[0].login_calls == []


@pytest.mark.asyncio
async def test_place_and_close_use_the_interface(caplog: pytest.LogCaptureFixture) -> None:
    broker, created = _broker()
    with caplog.at_level(logging.WARNING):
        sent = await broker.place_order(
            symbol="XAUUSD",
            side="buy",
            lot=0.1,
            stop=2290.0,
            take_profit=2320.0,
            comment="swing",
        )
    assert sent["ok"] is True
    assert sent["result"]["positionId"] == "77"
    assert "s3cret-pass" not in caplog.text
    request = created[0].requests[0]
    assert request["symbol"] == "XAUUSD"
    assert request["type"] == 0
    closed = await broker.close_order(position_id="55")
    assert closed["ok"] is True
    assert created[0].requests[1]["position"] == 55


@pytest.mark.asyncio
async def test_connection_retries_and_redacts_password() -> None:
    created: list[FakeMt5] = []
    calls = {"n": 0}

    def factory(host: str, port: int):
        calls["n"] += 1
        if calls["n"] < 3:
            raise Mt5ConnectionError("dial failed s3cret-pass")
        client = FakeMt5(host, port)
        created.append(client)
        return client

    broker = Mt5LinuxBroker(
        host="10.0.0.4",
        port=8001,
        login="10001",
        password="s3cret-pass",
        server="Broker-Demo",
        attempts=3,
        retry_delay=0,
        client_factory=factory,
    )
    result = await broker.connect()
    assert result["ok"] is True
    assert calls["n"] == 3
    assert redact_secret("dial failed s3cret-pass", "s3cret-pass") == "dial failed ***"


class RejectingMt5(FakeMt5):
    def login(self, login, password="", server="") -> bool:
        raise Mt5ConnectionError(f"rejected {password}")


@pytest.mark.asyncio
async def test_bad_login_returns_redacted_error() -> None:
    def factory(host: str, port: int) -> RejectingMt5:
        return RejectingMt5(host, port)

    broker = Mt5LinuxBroker(
        host="mt5.internal",
        port=8001,
        login="10001",
        password="bad",
        server="Broker-Demo",
        attempts=1,
        retry_delay=0,
        client_factory=factory,
    )
    result = await broker.connect()
    assert result["ok"] is False
    assert "bad" not in str(result["error"])
    assert "***" in str(result["error"])
