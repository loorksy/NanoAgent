from nanobot.trading.stage_events import emit_stage, stage_label


def test_stage_label_arabic() -> None:
    assert "السوق" in stage_label("market_data", "ar")


def test_emit_stage_wire() -> None:
    event = emit_stage("market_data", "running")
    wire = event.to_wire()
    assert wire["stage"] == "market_data"
    assert wire["status"] == "running"
