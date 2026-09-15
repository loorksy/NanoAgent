"""Plan lifecycle — sync terminal outcomes and archive."""

import pytest

from nanobot.trading.recommendations.followup import finalize_live_plan_if_closed
from nanobot.trading.recommendations.lifecycle import (
    list_session_archive,
    prepare_for_new_recommendation,
    sync_session_live_plan,
)
from nanobot.trading.recommendations.store import (
    latest_live_recommendation,
    store_recommendation,
    update_recommendation_status,
)
from nanobot.trading.types import (
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
    monkeypatch.setattr("nanobot.config.paths.get_data_dir", lambda: tmp_path)
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
    monkeypatch.setattr("nanobot.config.paths.get_data_dir", lambda: tmp_path)
    session_key = "websocket:archive-case"
    rec_id = store_recommendation(_sell_decision(), [], _market(), session_key=session_key)
    assert rec_id
    update_recommendation_status(rec_id, "in_trade")

    assert sync_session_live_plan(session_key, live_price=4298.0) is None
    archived = list_session_archive(session_key, category="invalidated")
    assert any(row["id"] == rec_id for row in archived)


@pytest.mark.asyncio
async def test_get_live_sync_clears_stale_waiting_row(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("nanobot.config.paths.get_data_dir", lambda: tmp_path)
    monkeypatch.setattr("nanobot.trading.recommendations.store.get_data_dir", lambda: tmp_path)
    session_key = "websocket:tool-sync"
    rec_id = store_recommendation(_sell_decision(), [], _market(), session_key=session_key)
    assert rec_id

    from nanobot.agent.tools.trading_chart import GetLiveRecommendationTool

    tool = GetLiveRecommendationTool(bus=None)

    class Q:
        mid = 4297.0
        bid = 4296.5
        ask = 4297.5
        symbol = "XAUUSD"
        tradeable = True

    monkeypatch.setattr("nanobot.agent.tools.trading_chart.fetch_quote", lambda *_a, **_k: Q())
    monkeypatch.setattr("nanobot.trading.recommendations.lifecycle.fetch_quote", lambda *_a, **_k: Q())
    monkeypatch.setattr(
        "nanobot.agent.tools.trading_chart.current_request_session_key",
        lambda: session_key,
    )
    monkeypatch.setattr(
        "nanobot.agent.tools.trading_chart.load_trading_config",
        lambda: type("C", (), {"oanda_configured": True})(),
    )

    import json

    payload = json.loads(await tool.execute())
    assert payload.get("has_live_plan") is False
    assert latest_live_recommendation(session_key) is None
