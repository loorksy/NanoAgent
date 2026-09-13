from nanobot.trading.capture_service import build_chart_snapshot_artifact


def test_build_chart_snapshot_artifact() -> None:
    artifact = build_chart_snapshot_artifact(
        [{"timeframe": "15m", "image": "data:image/jpeg;base64,YQ=="}],
        interval="15m",
        locale="en",
    )
    assert artifact is not None
    assert artifact["type"] == "chart_snapshot"
    assert "Gold chart snapshot" in artifact["title"]
