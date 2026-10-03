"""MetaAPI account linking keeps the broker form and does not store the password."""

from __future__ import annotations

import json

from mokli.config.loader import load_config, save_config
from mokli.trading.metaapi_accounts import (
    MetaApiLinkError,
    link_account,
    search_brokers,
    unlink_account,
)


def _isolate(tmp_path, monkeypatch) -> None:
    for name in ("METAAPI_TOKEN", "METAAPI_ACCOUNT_ID", "METAAPI_REGION"):
        monkeypatch.delenv(name, raising=False)
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps({"trading_metaapi": {"token": "tok", "region": "london"}}),
        encoding="utf-8",
    )


def test_link_account_provisions_and_omits_the_password(tmp_path, monkeypatch) -> None:
    _isolate(tmp_path, monkeypatch)
    path = tmp_path / "config.json"
    calls: list[tuple[str, str]] = []

    class Response:
        def __init__(self, status: int, payload: object) -> None:
            self.status_code = status
            self._payload = payload
            self.text = "" if payload == {} else json.dumps(payload)

        def json(self) -> object:
            return self._payload

    class Client:
        def __init__(self, timeout: float) -> None:
            del timeout

        def __enter__(self) -> Client:
            return self

        def __exit__(self, *_args: object) -> bool:
            return False

        def post(self, url: str, headers: dict[str, str], json: dict[str, object]) -> Response:
            calls.append(("post", url))
            assert headers["auth-token"] == "tok"
            if url.endswith("/accounts"):
                assert json["login"] == "1001"
                assert json["password"] == "secret"
                assert json["server"] == "Broker-Demo"
                assert json["platform"] == "mt5"
                return Response(201, {"id": "acc-1", "state": "DEPLOYING", "region": "london"})
            assert url.endswith("/acc-1/deploy")
            return Response(204, {})

        def get(self, url: str, headers: dict[str, str], params: dict[str, str] | None = None) -> Response:
            del headers, params
            calls.append(("get", url))
            return Response(
                200,
                {
                    "id": "acc-1",
                    "state": "DEPLOYED",
                    "connectionStatus": "CONNECTED",
                    "region": "london",
                    "login": "1001",
                    "server": "Broker-Demo",
                    "name": "Gold",
                },
            )

        def delete(self, url: str, headers: dict[str, str]) -> Response:
            del url, headers
            raise AssertionError("delete")

    monkeypatch.setattr("mokli.trading.metaapi_accounts.httpx.Client", Client)
    payload = link_account(
        login="1001",
        password="secret",
        server="Broker-Demo",
        company="Broker",
        config_path=path,
    )
    assert payload["connected"] is True
    assert payload["login"] == "1001"
    saved = load_config(path).trading_metaapi
    assert saved.account_id == "acc-1"
    assert saved.region == "london"
    assert saved.login == "1001"
    assert saved.server == "Broker-Demo"
    assert saved.token == "tok"
    raw = path.read_text(encoding="utf-8")
    assert "secret" not in raw
    assert [item[0] for item in calls] == ["post", "post", "get"]


def test_search_uses_metaapi_servers(monkeypatch) -> None:
    monkeypatch.setenv("METAAPI_TOKEN", "tok")

    class Response:
        status_code = 200
        text = "[]"

        def json(self) -> list[dict[str, str]]:
            return [{"company": "Raw Trading Ltd", "server": "ICMarketsSC-Demo"}]

    class Client:
        def __init__(self, timeout: float) -> None:
            del timeout

        def __enter__(self) -> Client:
            return self

        def __exit__(self, *_args: object) -> bool:
            return False

        def get(self, url: str, headers: dict[str, str], params: dict[str, str] | None = None) -> Response:
            assert url.endswith("/known-mt-servers/5")
            assert headers["auth-token"] == "tok"
            assert params == {"query": "ic"}
            return Response()

    monkeypatch.setattr("mokli.trading.metaapi_accounts.httpx.Client", Client)
    rows = search_brokers("ic")
    assert rows == [
        {"name": "Raw Trading Ltd", "label": "Raw Trading Ltd", "servers": ["ICMarketsSC-Demo"]}
    ]


def test_unlink_clears_the_saved_account(tmp_path, monkeypatch) -> None:
    _isolate(tmp_path, monkeypatch)
    path = tmp_path / "config.json"
    loaded = load_config(path)
    loaded.trading_metaapi.account_id = "acc-1"
    loaded.trading_metaapi.login = "1001"
    save_config(loaded, path)

    class Response:
        status_code = 204
        text = ""

        def json(self) -> dict[str, str]:
            return {}

    class Client:
        def __init__(self, timeout: float) -> None:
            del timeout

        def __enter__(self) -> Client:
            return self

        def __exit__(self, *_args: object) -> bool:
            return False

        def delete(self, url: str, headers: dict[str, str]) -> Response:
            assert url.endswith("/acc-1")
            assert headers["auth-token"] == "tok"
            return Response()

    monkeypatch.setattr("mokli.trading.metaapi_accounts.httpx.Client", Client)
    payload = unlink_account(config_path=path)
    assert payload["connected"] is False
    saved = load_config(path).trading_metaapi
    assert saved.account_id == ""
    assert saved.login == ""
    assert saved.token == "tok"


def test_link_requires_a_token(tmp_path, monkeypatch) -> None:
    _isolate(tmp_path, monkeypatch)
    path = tmp_path / "config.json"
    path.write_text("{}", encoding="utf-8")
    try:
        link_account(login="1", password="pw", server="Demo", config_path=path)
    except MetaApiLinkError as exc:
        assert "METAAPI_TOKEN" in exc.message
    else:
        raise AssertionError("expected token error")
