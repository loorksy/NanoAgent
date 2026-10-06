"""Plan lifecycle — sync terminal outcomes and archive."""

import pytest

from mokli.trading.recommendations.followup import finalize_live_plan_if_closed
from mokli.trading.recommendations.lifecycle import (
    close_plan_for_session,
    list_session_archive,
    prepare_for_new_recommendation,
    sync_session_live_plan,
)
from mokli.trading.recommendations.store import (
    latest_live_recommendation,
    store_recommendation,
    update_recommendation_status,
)
from mokli.trading.types import (
    AgentMarketContext,
    AgentRecommendation,
    Candle,
    FinalDecisionResult,
    MarketSync,
)


def _sell_decision() -> FinalDecisionResult:
    return FinalDecisionResult(
        decision="sell",
        confidence=0.8,
        summary="Sell plan",
        key_reasons=[],
        risk_warnings=[],
        recommendation=AgentRecommendation(
            action="sell",
            entry=4285.09,
            stop_loss=4294.99,
            targets=[4274.38, 4263.68],
            interval="15m",
        ),
    )


def _market() -> AgentMarketContext:
    return AgentMarketContext(
        symbol="XAUUSD",
        interval="15m",
        candles=[Candle(1, 1, 1, 1, 4285, 0)],
        last_close=4285.0,
        atr=8.0,
        sync=MarketSync(ok=True),
    )


def test_invalidated_plan_stops_blocking_new_rec(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("mokli.config.paths.get_data_dir", lambda: tmp_path)
    session_key = "websocket:invalidated-case"
    rec_id = store_recommendation(_sell_decision(), [], _market(), session_key=session_key)
    assert rec_id
    update_recommendation_status(rec_id, "waiting")

    live = latest_live_recommendation(session_key)
    assert live is not None
    assert finalize_live_plan_if_closed(live, live_price=4297.70) is None
    assert latest_live_recommendation(session_key) is None

    prep = prepare_for_new_recommendation(session_key)
    assert prep["live_plan"] is None
    assert prep["action"] in {"already_clear", "auto_archived"}


def test_sync_archives_invalidated_row(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("mokli.config.paths.get_data_dir", lambda: tmp_path)
    session_key = "websocket:archive-case"
    rec_id = store_recommendation(_sell_decision(), [], _market(), session_key=session_key)
    assert rec_id
    update_recommendation_status(rec_id, "in_trade")

    assert sync_session_live_plan(session_key, live_price=4298.0) is None
    archived = list_session_archive(session_key, category="invalidated")
    assert any(row["id"] == rec_id for row in archived)


@pytest.mark.asyncio
async def test_get_live_sync_clears_stale_waiting_row(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("mokli.config.paths.get_data_dir", lambda: tmp_path)
    monkeypatch.setattr("mokli.trading.recommendations.store.get_data_dir", lambda: tmp_path)
    session_key = "websocket:tool-sync"
    rec_id = store_recommendation(_sell_decision(), [], _market(), session_key=session_key)
    assert rec_id

    from mokli.agent.tools.trading_chart import GetLiveRecommendationTool

    tool = GetLiveRecommendationTool(bus=None)

    class Q:
        mid = 4297.0
        bid = 4296.5
        ask = 4297.5
        symbol = "XAUUSD"
        tradeable = True

    calls = {"resolve": 0, "direct": 0}

    def _resolve(symbol: str = "XAUUSD", config: object | None = None):
        del symbol, config
        calls["resolve"] += 1
        return Q(), "metaapi"

    def _direct(*_args: object, **_kwargs: object) -> None:
        calls["direct"] += 1
        raise AssertionError("direct OANDA quote")

    monkeypatch.setattr("mokli.trading.market_context.resolve_live_quote", _resolve)
    monkeypatch.setattr("mokli.trading.oanda.fetch_quote", _direct)
    monkeypatch.setattr(
        "mokli.agent.tools.trading_chart.current_request_session_key",
        lambda: session_key,
    )
    monkeypatch.setattr(
        "mokli.agent.tools.trading_chart.load_trading_config",
        lambda: type("C", (), {"oanda_configured": True})(),
    )

    import json

    payload = json.loads(await tool.execute())
    assert payload.get("has_live_plan") is False
    assert latest_live_recommendation(session_key) is None
    assert calls == {"resolve": 1, "direct": 0}


def test_prepare_new_reads_one_quote_for_a_live_plan(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("mokli.config.paths.get_data_dir", lambda: tmp_path)
    monkeypatch.setattr("mokli.trading.recommendations.store.get_data_dir", lambda: tmp_path)
    session_key = "websocket:prepare-once"
    rec_id = store_recommendation(_sell_decision(), [], _market(), session_key=session_key)
    assert rec_id
    update_recommendation_status(rec_id, "waiting")

    class Q:
        mid = 4286.0

    calls = {"resolve": 0, "direct": 0}

    def _resolve(symbol: str = "XAUUSD", config: object | None = None):
        del symbol, config
        calls["resolve"] += 1
        return Q(), "metaapi"

    def _direct(*_args: object, **_kwargs: object) -> None:
        calls["direct"] += 1
        raise AssertionError("direct OANDA quote")

    monkeypatch.setattr("mokli.trading.market_context.resolve_live_quote", _resolve)
    monkeypatch.setattr("mokli.trading.oanda.fetch_quote", _direct)

    prep = prepare_for_new_recommendation(session_key)
    assert prep["action"] == "live_remains"
    assert calls == {"resolve": 1, "direct": 0}

    closed = close_plan_for_session(
        session_key,
        live_price=4286.0,
        price_known=True,
    )
    assert closed["ok"] is True
    assert calls == {"resolve": 1, "direct": 0}


def test_prepare_new_does_not_fetch_when_the_quote_is_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("mokli.config.paths.get_data_dir", lambda: tmp_path)
    monkeypatch.setattr("mokli.trading.recommendations.store.get_data_dir", lambda: tmp_path)
    session_key = "websocket:prepare-missing"
    rec_id = store_recommendation(_sell_decision(), [], _market(), session_key=session_key)
    assert rec_id

    calls = {"resolve": 0, "direct": 0}

    def _resolve(symbol: str = "XAUUSD", config: object | None = None):
        del symbol, config
        calls["resolve"] += 1
        return None, None

    def _direct(*_args: object, **_kwargs: object) -> None:
        calls["direct"] += 1
        raise AssertionError("direct OANDA quote")

    monkeypatch.setattr("mokli.trading.market_context.resolve_live_quote", _resolve)
    monkeypatch.setattr("mokli.trading.oanda.fetch_quote", _direct)

    prep = prepare_for_new_recommendation(session_key)
    assert prep["action"] == "live_remains"
    assert calls == {"resolve": 1, "direct": 0}
