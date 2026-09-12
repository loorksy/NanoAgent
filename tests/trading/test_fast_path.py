import asyncio

from nanobot.trading.fast_path import try_gold_fast_path
from nanobot.trading.turn_planner import plan_turn


def test_plan_turn_price_query_arabic() -> None:
    turn = plan_turn("كم سعر الذهب؟")
    assert turn.mode == "market_data_only"
    assert turn.intent.kind == "price_query"


def test_fast_path_skips_analysis_request() -> None:
    result = asyncio.run(
        try_gold_fast_path(
            "حلل الذهب واعطني توصية",
            channel="websocket",
            chat_id="ws:1",
        )
    )
    assert result is None


def test_fast_path_oanda_unconfigured() -> None:
    result = asyncio.run(
        try_gold_fast_path(
            "gold price",
            channel="websocket",
            chat_id="ws:1",
        )
    )
    assert result is not None
    assert "OANDA" in result.content
