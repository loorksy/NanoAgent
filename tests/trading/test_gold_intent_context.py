import asyncio

from nanobot.agent.tools.context import RequestContext
from nanobot.trading.gold_intent_context import gold_intent_runtime_context


def test_gold_intent_context_for_analysis() -> None:
    request = RequestContext(
        channel="websocket",
        chat_id="ws:1",
        session_key="websocket:1",
        original_user_text="حلل الذهب الآن",
    )
    block = asyncio.run(gold_intent_runtime_context(request))
    assert block is not None
    assert "gold_analysis" in block.content
    assert "analyze_gold" in block.content


def test_gold_intent_context_telegram_does_not_repeat_card() -> None:
    request = RequestContext(
        channel="telegram",
        chat_id="123",
        session_key="telegram:123",
        original_user_text="اعطيني توصية",
    )
    block = asyncio.run(gold_intent_runtime_context(request))
    assert block is not None
    assert "Do not repeat entry" in block.content


def test_gold_intent_context_skips_general_chat() -> None:
    request = RequestContext(
        channel="websocket",
        chat_id="ws:1",
        session_key="websocket:1",
        original_user_text="hello there",
    )
    block = asyncio.run(gold_intent_runtime_context(request))
    assert block is None
