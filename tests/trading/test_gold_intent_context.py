import asyncio

from mokli.agent.tools.context import RequestContext
from mokli.trading.gold_intent_context import gold_intent_runtime_context


def test_gold_intent_context_none_without_live_plan() -> None:
    request = RequestContext(
        channel="websocket",
        chat_id="ws:1",
        session_key="websocket:1",
        original_user_text="حلل الذهب الآن",
    )
    block = asyncio.run(gold_intent_runtime_context(request))
    assert block is None


def test_gold_intent_context_with_live_plan(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("mokli.config.paths.get_data_dir", lambda: tmp_path)
    monkeypatch.setattr("mokli.trading.recommendations.store.get_data_dir", lambda: tmp_path)

    from mokli.trading.recommendations.store import store_recommendation
    from mokli.trading.types import (
        AgentMarketContext,
        AgentRecommendation,
        Candle,
        FinalDecisionResult,
        MarketSync,
    )

    decision = FinalDecisionResult(
        decision="sell",
        confidence=0.8,
        summary="Sell plan",
        key_reasons=[],
        risk_warnings=[],
        recommendation=AgentRecommendation(
            action="sell",
            entry=2400.0,
            stop_loss=2415.0,
            targets=[2380.0],
            interval="15m",
        ),
    )
    market = AgentMarketContext(
        symbol="XAUUSD",
        interval="15m",
        candles=[Candle(1, 1, 1, 1, 2400, 0)],
        last_close=2400.0,
        atr=8.0,
        sync=MarketSync(ok=True),
    )
    store_recommendation(decision, [], market, session_key="websocket:1")

    request = RequestContext(
        channel="websocket",
        chat_id="ws:1",
        session_key="websocket:1",
        original_user_text="اعطيني توصية",
    )
    block = asyncio.run(gold_intent_runtime_context(request))
    assert block is not None
    assert "live SELL" in block.content
    assert "One live recommendation" in block.content


def test_gold_intent_context_telegram_does_not_repeat_card(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("mokli.config.paths.get_data_dir", lambda: tmp_path)
    monkeypatch.setattr("mokli.trading.recommendations.store.get_data_dir", lambda: tmp_path)

    from mokli.trading.recommendations.store import store_recommendation
    from mokli.trading.types import (
        AgentMarketContext,
        AgentRecommendation,
        Candle,
        FinalDecisionResult,
        MarketSync,
    )

    decision = FinalDecisionResult(
        decision="buy",
        confidence=0.8,
        summary="Buy plan",
        key_reasons=[],
        risk_warnings=[],
        recommendation=AgentRecommendation(
            action="buy",
            entry=2400.0,
            stop_loss=2385.0,
            targets=[2420.0],
            interval="15m",
        ),
    )
    market = AgentMarketContext(
        symbol="XAUUSD",
        interval="15m",
        candles=[Candle(1, 1, 1, 1, 2400, 0)],
        last_close=2400.0,
        atr=8.0,
        sync=MarketSync(ok=True),
    )
    store_recommendation(decision, [], market, session_key="telegram:123")

    request = RequestContext(
        channel="telegram",
        chat_id="123",
        session_key="telegram:123",
        original_user_text="اعطيني توصية",
    )
    block = asyncio.run(gold_intent_runtime_context(request))
    assert block is not None
    assert "without repeating entry" in block.content


def test_live_plan_grades_once_off_the_event_loop(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("mokli.config.paths.get_data_dir", lambda: tmp_path)
    monkeypatch.setattr("mokli.trading.recommendations.store.get_data_dir", lambda: tmp_path)

    from types import SimpleNamespace

    from mokli.trading.recommendations.store import store_recommendation
    from mokli.trading.types import (
        AgentMarketContext,
        AgentRecommendation,
        Candle,
        FinalDecisionResult,
        MarketSync,
    )

    decision = FinalDecisionResult(
        decision="sell",
        confidence=0.8,
        summary="Sell plan",
        key_reasons=[],
        risk_warnings=[],
        recommendation=AgentRecommendation(
            action="sell",
            entry=2400.0,
            stop_loss=2415.0,
            targets=[2380.0],
            interval="15m",
        ),
    )
    market = AgentMarketContext(
        symbol="XAUUSD",
        interval="15m",
        candles=[Candle(1, 1, 1, 1, 2400, 0)],
        last_close=2400.0,
        atr=8.0,
        sync=MarketSync(ok=True),
    )
    store_recommendation(decision, [], market, session_key="websocket:1")

    calls = {"resolve": 0, "direct": 0}

    def _resolve(symbol: str = "XAUUSD", config: object | None = None):
        del symbol, config
        calls["resolve"] += 1
        return SimpleNamespace(mid=2390.0), "metaapi"

    def _direct(*_args: object, **_kwargs: object) -> None:
        calls["direct"] += 1
        raise AssertionError("direct OANDA quote")

    monkeypatch.setattr("mokli.trading.market_context.resolve_live_quote", _resolve)
    monkeypatch.setattr("mokli.trading.oanda.fetch_quote", _direct)

    request = RequestContext(
        channel="websocket",
        chat_id="ws:1",
        session_key="websocket:1",
        original_user_text="شكرا",
    )
    block = asyncio.run(gold_intent_runtime_context(request))
    assert calls == {"resolve": 1, "direct": 0}
    assert block is not None
    assert "live SELL" in block.content
    assert "Platform live" not in block.content
    assert "2390" not in block.content


def test_gold_intent_context_skips_general_chat() -> None:
    request = RequestContext(
        channel="websocket",
        chat_id="ws:1",
        session_key="websocket:1",
        original_user_text="hello there",
    )
    block = asyncio.run(gold_intent_runtime_context(request))
    assert block is None
