import json

from mokli.trading.capture_service import build_chart_snapshot_artifact, chart_capture_tool_result
from mokli.utils.helpers import estimate_prompt_tokens


def test_build_chart_snapshot_artifact() -> None:
    artifact = build_chart_snapshot_artifact(
        [{"timeframe": "15m", "image": "data:image/jpeg;base64,YQ=="}],
        interval="15m",
        locale="en",
    )
    assert artifact is not None
    assert artifact["type"] == "chart_snapshot"
    assert "Gold chart snapshot" in artifact["title"]


def test_chart_capture_result_omits_image_bytes() -> None:
    image = "data:image/jpeg;base64," + ("A" * 8000)
    payload = {
        "ok": True,
        "interval": "15m",
        "locale": "en",
        "artifacts": [{"image": image}],
        "chartSnapshots": [{"timeframe": "15m", "image": image}],
    }
    raw = json.dumps(payload)
    brief = chart_capture_tool_result(payload)
    before = estimate_prompt_tokens([{"role": "tool", "content": raw}], None)
    after = estimate_prompt_tokens([{"role": "tool", "content": brief}], None)
    assert "data:image" not in brief
    assert image not in brief
    assert payload["chartSnapshots"][0]["image"] == image
    assert after < before
    assert "15m" in brief
    print(f"TOKEN_CHART before={before} after={after}")
