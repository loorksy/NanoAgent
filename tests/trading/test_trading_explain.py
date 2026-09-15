"""Trading explain path — why questions stay on the kernel."""

import pytest

from nanobot.trading.explain import build_trading_explain, last_trading_wire_from_messages
from nanobot.trading.fast_path import try_gold_fast_path
from nanobot.trading.operator_keywords import wants_trading_explain


def test_wants_trading_explain_arabic() -> None:
    assert wants_trading_explain("ليش")
    assert wants_trading_explain("لماذا")
    assert not wants_trading_explain("اعطيني توصية جديدة")


def test_last_trading_wire_from_messages() -> None:
    messages = [
        {"role": "user", "content": "حلل"},
        {"role": "assistant", "content": "WAIT", "_trading_wire": {"decision": "wait", "summary": "x"}},
    ]
    assert last_trading_wire_from_messages(messages)["decision"] == "wait"


def test_build_trading_explain_arabic() -> None:
    text = build_trading_explain(
        {
            "decision": "wait",
            "summary": "لم يستطع مُجمّع التداول إصدار توصية مبنية على الأدلة المتاحة.",
            "refusalSummary": "مُجمّع التداول غير متاح",
            "keyReasons": ["عائق تشغيلي"],
        },
        locale="ar",
    )
    assert "نواة التداول" in text
    assert "عائق تشغيلي" in text


@pytest.mark.asyncio
async def test_fast_path_explain_does_not_fall_through() -> None:
    wire = {
        "decision": "wait",
        "summary": "blocked",
        "refusalSummary": "kernel",
    }
    result = await try_gold_fast_path(
        "ليش",
        channel="websocket",
        chat_id="ws:1",
        last_trading_wire=wire,
    )
    assert result is not None
    assert "نواة التداول" in result.content or "Trading kernel" in result.content
