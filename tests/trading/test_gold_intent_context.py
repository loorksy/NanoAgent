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


def test_gold_intent_and_kernel_share_one_live_grade(tmp_path, monkeypatch) -> None:
    """The intent note and the kernel block grade one tick. A price read still fetches."""
    import json
    import time

    monkeypatch.setattr("mokli.config.paths.get_data_dir", lambda: tmp_path)
    monkeypatch.setattr("mokli.trading.recommendations.store.get_data_dir", lambda: tmp_path)

    from mokli.agent.tools.context import request_context
    from mokli.agent.tools.trading_kernel import RunTradingKernelTool
    from mokli.trading.recommendations.lifecycle import grade_session_plan
    from mokli.trading.recommendations.store import (
        close_live_recommendation,
        latest_live_recommendation,
        store_recommendation,
    )
    from mokli.trading.turn_session import TurnSession, turn_session_scope
    from mokli.trading.types import (
        AgentMarketContext,
        AgentRecommendation,
        Candle,
        FinalDecisionResult,
        MarketSync,
    )

    session_key = "websocket:shared-grade"
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
    assert store_recommendation(decision, [], market, session_key=session_key)

    calls = {"resolve": 0}

    def _resolve(symbol: str = "XAUUSD", config: object | None = None):
        del symbol, config
        calls["resolve"] += 1
        time.sleep(0.2)
        quote = type("Q", (), {"mid": 2390.0, "bid": 2389.5, "ask": 2390.5, "symbol": "XAUUSD"})()
        return quote, "metaapi"

    def _direct(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("direct OANDA quote")

    async def _no_team(*_args: object, **_kwargs: object) -> dict[str, str]:
        raise AssertionError("team started")

    monkeypatch.setattr("mokli.trading.market_context.resolve_live_quote", _resolve)
    monkeypatch.setattr("mokli.trading.oanda.fetch_quote", _direct)
    monkeypatch.setattr("mokli.trading.teams.runtime.run_swarm", _no_team)

    request = RequestContext(
        channel="websocket",
        chat_id="ws:1",
        session_key=session_key,
        original_user_text="هل أشتري الذهب؟",
    )
    tool = RunTradingKernelTool(bus=object(), subagent_manager=None)
    ctx = RequestContext(channel="websocket", chat_id="ws:1", session_key=session_key)

    async def _both() -> None:
        await gold_intent_runtime_context(request)
        payload = json.loads(await tool.execute(decision_review=True))
        assert payload["reason_key"] == "trading.live_plan_active"

    started = time.perf_counter()
    with request_context(ctx), turn_session_scope(TurnSession()):
        asyncio.run(_both())
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        assert calls["resolve"] == 1
        shown = asyncio.run(grade_session_plan(session_key))
        assert shown[0] is not None
        assert calls["resolve"] == 2
        row = latest_live_recommendation(session_key)
        assert row is not None
        assert close_live_recommendation(str(row["id"]))
        decision.recommendation.entry = 2410.0
        assert store_recommendation(decision, [], market, session_key=session_key)
        asyncio.run(gold_intent_runtime_context(request))
        assert calls["resolve"] == 3
    print(f"LIVE_GRADE before_ms=400 after_ms={elapsed_ms}")
    assert elapsed_ms < 350

    with turn_session_scope(TurnSession()):
        asyncio.run(gold_intent_runtime_context(request))
    assert calls["resolve"] == 4


def test_gold_intent_context_skips_general_chat() -> None:
    request = RequestContext(
        channel="websocket",
        chat_id="ws:1",
        session_key="websocket:1",
        original_user_text="hello there",
    )
    block = asyncio.run(gold_intent_runtime_context(request))
    assert block is None
