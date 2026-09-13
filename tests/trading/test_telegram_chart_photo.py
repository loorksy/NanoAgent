import asyncio
import base64
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from nanobot.trading.stage_delivery import TradingStagePublisher


def test_publish_result_attaches_telegram_chart_photo() -> None:
    bus = MagicMock()
    bus.publish_outbound = AsyncMock()
    publisher = TradingStagePublisher(bus, channel="telegram", chat_id="123")
    image = base64.b64encode(b"jpegbytes").decode("ascii")
    payload = {
        "decision": "buy",
        "summary": "Gold breakout",
        "confidence": 0.8,
        "recommendation": {"entry": 2400, "stopLoss": 2390, "targets": [2410]},
        "chartSnapshots": [{"timeframe": "15m", "image": f"data:image/jpeg;base64,{image}"}],
    }
    asyncio.run(publisher.publish_result(payload))
    outbound = bus.publish_outbound.await_args_list[0].args[0]
    assert outbound.media
    assert outbound.metadata.get("parse_mode") == "HTML"
    assert "توصية" in outbound.content
    chart_path = outbound.media[0]
    assert Path(chart_path).is_file(), "chart temp file must survive until channel delivery"
