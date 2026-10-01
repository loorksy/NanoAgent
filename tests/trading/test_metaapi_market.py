"""MetaAPI live quote client."""

from __future__ import annotations

from mokli.trading.config import TradingConfig
from mokli.trading.metaapi_market import fetch_metaapi_quote


def _config() -> TradingConfig:
    return TradingConfig(
        oanda_api_token=None,
        oanda_account_id=None,
        oanda_env="practice",
        metaapi_token="tok",
        metaapi_account_id="acc",
        metaapi_region="london",
    )


def test_metaapi_quote_reads_the_cloud_price(monkeypatch) -> None:
    seen: dict[str, object] = {}

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"bid": 10.0, "ask": 12.0, "time": "2026-09-29T12:00:00.000Z"}

    class Client:
        def __init__(self, timeout: float) -> None:
            del timeout

        def __enter__(self) -> Client:
            return self

        def __exit__(self, *_args: object) -> bool:
            return False

        def get(self, url: str, headers: dict[str, str]) -> Response:
            seen["url"] = url
            seen["token"] = headers["auth-token"]
            return Response()

    monkeypatch.setattr("mokli.trading.metaapi_market.httpx.Client", Client)
    quote = fetch_metaapi_quote("XAUUSD", config=_config())
    assert quote is not None
    assert quote.bid == 10.0
    assert quote.ask == 12.0
    assert seen["token"] == "tok"
    assert seen["url"] == (
        "https://mt-client-api-v1.london.agiliumtrade.ai"
        "/users/current/accounts/acc/symbols/XAUUSD/current-price"
    )
    assert "tok" not in str(seen["url"])


def test_metaapi_quote_skips_when_unconfigured() -> None:
    config = TradingConfig(
        oanda_api_token=None,
        oanda_account_id=None,
        oanda_env="practice",
    )
    assert fetch_metaapi_quote("XAUUSD", config=config) is None
