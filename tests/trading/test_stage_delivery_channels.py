import asyncio
from unittest.mock import AsyncMock, MagicMock

from nanobot.trading.stage_delivery import TradingStagePublisher


def test_publish_result_sends_telegram_html_card() -> None:
    bus = MagicMock()
    bus.publish_outbound = AsyncMock()
    publisher = TradingStagePublisher(bus, channel="telegram", chat_id="123")
    payload = {
        "decision": "buy",
        "summary": "Gold breakout",
        "confidence": 0.8,
        "recommendation": {"entry": 2400, "stopLoss": 2390, "targets": [2410]},
    }
    asyncio.run(publisher.publish_result(payload))
    assert bus.publish_outbound.await_count >= 2
    html_calls = [
        call
        for call in bus.publish_outbound.await_args_list
        if call.args[0].metadata.get("parse_mode") == "HTML"
    ]
    assert len(html_calls) == 1
    assert "<b>Gold BUY</b>" in html_calls[0].args[0].content


def test_publish_result_sends_whatsapp_plain_card() -> None:
    bus = MagicMock()
    bus.publish_outbound = AsyncMock()
    publisher = TradingStagePublisher(bus, channel="whatsapp", chat_id="123@s.whatsapp.net")
    payload = {
        "decision": "sell",
        "summary": "Rejection at supply",
        "confidence": 0.7,
        "recommendation": {"entry": 2400, "stopLoss": 2410, "targets": [2385]},
    }
    asyncio.run(publisher.publish_result(payload))
    wa_calls = [
        call.args[0].content
        for call in bus.publish_outbound.await_args_list
        if "*Gold SELL*" in call.args[0].content
    ]
    assert len(wa_calls) == 1
