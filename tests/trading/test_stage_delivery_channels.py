import asyncio
from unittest.mock import AsyncMock, MagicMock

from nanobot.bus.events import OUTBOUND_META_AGENT_UI
from nanobot.channels.telegram.trading_progress import TRADING_PROGRESS_META
from nanobot.trading.stage_delivery import TradingStagePublisher
from nanobot.trading.stage_events import emit_stage


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
    html_calls = [
        call
        for call in bus.publish_outbound.await_args_list
        if call.args[0].metadata.get("parse_mode") == "HTML"
    ]
    assert len(html_calls) == 1
    content = html_calls[0].args[0].content
    assert "توصية" in content
    assert "شراء" in content
    assert "$2,400.00" in content
    assert html_calls[0].args[0].event is None


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
        if "توصية" in call.args[0].content
    ]
    assert len(wa_calls) == 1
    assert "بيع" in wa_calls[0]
    assert "$2,400.00" in wa_calls[0]


def test_telegram_stages_publish_one_checklist_not_agent_ui() -> None:
    bus = MagicMock()
    bus.publish_outbound = AsyncMock()
    publisher = TradingStagePublisher(bus, channel="telegram", chat_id="123")

    async def _run() -> None:
        await publisher.open_chart("15m")
        await publisher._publish(emit_stage("market_data", "running"))
        await publisher._publish(emit_stage("market_data", "done"))

    asyncio.run(_run())
    assert bus.publish_outbound.await_count == 2
    for call in bus.publish_outbound.await_args_list:
        outbound = call.args[0]
        assert OUTBOUND_META_AGENT_UI not in outbound.metadata
        assert outbound.metadata.get(TRADING_PROGRESS_META) is True
        assert "Opening gold chart" not in outbound.content
        assert "Market data" not in outbound.content
        assert "جاري جلب بيانات السوق" in outbound.content


def test_whatsapp_stages_publish_single_progress_line() -> None:
    bus = MagicMock()
    bus.publish_outbound = AsyncMock()
    publisher = TradingStagePublisher(bus, channel="whatsapp", chat_id="123@s.whatsapp.net")

    async def _run() -> None:
        await publisher.open_chart("15m")
        await publisher._publish(emit_stage("market_data", "running"))
        await publisher._publish(emit_stage("structure", "running"))

    asyncio.run(_run())
    assert bus.publish_outbound.await_count == 1
    outbound = bus.publish_outbound.await_args_list[0].args[0]
    assert outbound.content == "⏳ جاري تحليل الذهب…"
    assert outbound.metadata.get(TRADING_PROGRESS_META) is True


def test_publish_result_flushes_pending_stage_tasks() -> None:
    bus = MagicMock()
    published: list[str] = []

    async def _capture(msg) -> None:
        published.append(msg.content)

    bus.publish_outbound = AsyncMock(side_effect=_capture)
    publisher = TradingStagePublisher(bus, channel="telegram", chat_id="123")

    async def _run() -> None:
        publisher.sync_emit(emit_stage("drawing", "done"))
        await publisher.publish_result(
            {
                "decision": "wait",
                "summary": "No setup",
                "confidence": 0.3,
                "recommendation": {"action": "wait"},
            }
        )

    asyncio.run(_run())
    assert any("رسم التحليل على الشارت" in item for item in published)
    assert published[-1].startswith("⚪")


def test_websocket_keeps_agent_ui_stages() -> None:
    bus = MagicMock()
    bus.publish_outbound = AsyncMock()
    publisher = TradingStagePublisher(bus, channel="websocket", chat_id="ws:1")

    async def _run() -> None:
        await publisher.open_chart("15m")
        await publisher._publish(emit_stage("market_data", "running"))

    asyncio.run(_run())
    kinds = [
        call.args[0].metadata[OUTBOUND_META_AGENT_UI]["kind"]
        for call in bus.publish_outbound.await_args_list
    ]
    assert kinds == ["trading_chart_open", "trading_stage"]
