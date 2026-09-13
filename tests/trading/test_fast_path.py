import asyncio

from nanobot.trading.fast_path import try_gold_fast_path
from nanobot.trading.intent_router import resolve_team_preset
from nanobot.trading.turn_planner import plan_turn


def test_plan_turn_price_query_arabic() -> None:
    turn = plan_turn("كم سعر الذهب؟")
    assert turn.mode == "market_data_only"
    assert turn.intent.kind == "price_query"


def test_plan_turn_chart_capture() -> None:
    turn = plan_turn("أرسل صورة شارت الذهب")
    assert turn.mode == "chart_capture"
    assert turn.intent.kind == "chart_image"


def test_fast_path_runs_analysis_for_arabic_request() -> None:
    turn = plan_turn("حلل الذهب واعطني توصية")
    assert turn.mode == "full_analysis"
    assert turn.intent.confidence >= 0.75


def test_fast_path_runs_recommendation_without_gold_keyword() -> None:
    turn = plan_turn("اعطيني توصية")
    assert turn.mode == "full_analysis"
    assert turn.intent.kind == "recommendation"


def test_resolve_team_preset_war_room() -> None:
    assert resolve_team_preset("شغّل غرفة الأخبار") == "gold_news_war_room"


def test_fast_path_skips_low_confidence_gold_mention() -> None:
    result = asyncio.run(
        try_gold_fast_path(
            "I like gold stories",
            channel="websocket",
            chat_id="ws:1",
        )
    )
    assert result is None


def test_fast_path_recommendation_does_not_skip_to_llm() -> None:
    result = asyncio.run(
        try_gold_fast_path(
            "اعطيني توصية",
            channel="telegram",
            chat_id="1",
        )
    )
    assert result is not None


def test_fast_path_oanda_unconfigured() -> None:
    result = asyncio.run(
        try_gold_fast_path(
            "gold price",
            channel="websocket",
            chat_id="ws:1",
        )
    )
    assert result is not None
    assert "Market data" in result.content or "بيانات السوق" in result.content
