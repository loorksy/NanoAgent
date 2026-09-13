import base64

from nanobot.trading.chart_photo import (
    cleanup_chart_snapshot,
    lead_chart_frame,
    write_chart_snapshot_file,
)


def test_lead_chart_frame_prefers_first_image():
    frames = [
        {"timeframe": "15m", "context": "no image"},
        {"timeframe": "1h", "image": "data:image/png;base64,AA=="},
    ]
    assert lead_chart_frame(frames)["timeframe"] == "1h"


def test_write_chart_snapshot_file_roundtrip():
    payload = base64.b64encode(b"fakejpeg").decode("ascii")
    path = write_chart_snapshot_file(
        {"timeframe": "15m", "image": f"data:image/jpeg;base64,{payload}"},
    )
    assert path is not None
    try:
        from pathlib import Path

        assert Path(path).exists()
        assert Path(path).read_bytes() == b"fakejpeg"
    finally:
        cleanup_chart_snapshot(path)
