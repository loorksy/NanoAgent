"""CFTC-style positioning snapshot (R9). Parsing is local; fetch is injected."""

from __future__ import annotations

from collections.abc import Callable
from typing import cast


def cot_bias(spec_net: int) -> str:
    if spec_net > 0:
        return "bullish"
    if spec_net < 0:
        return "bearish"
    return "neutral"


def _int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return 0
    try:
        return int(float(value))
    except ValueError:
        return 0


def snapshot_from_rows(rows: list[dict[str, object]], *, market: str = "gold") -> dict[str, object]:
    if not rows:
        return {
            "market": market,
            "commercial_net": 0,
            "spec_net": 0,
            "bias": "neutral",
            "notice_key": "cot.bias_neutral",
            "available": False,
        }
    last = rows[-1]
    spec_net = _int(last.get("spec_net"))
    bias = cot_bias(spec_net)
    notice = {
        "bullish": "cot.bias_bullish",
        "bearish": "cot.bias_bearish",
        "neutral": "cot.bias_neutral",
    }[bias]
    return {
        "market": market,
        "commercial_net": _int(last.get("commercial_net")),
        "spec_net": spec_net,
        "bias": bias,
        "notice_key": notice,
        "available": True,
    }


def fetch_cot(
    http_get: Callable[[str], list[dict[str, object]]],
    url: str,
) -> dict[str, object]:
    payload = http_get(url)
    rows = cast(list[dict[str, object]], payload)
    return snapshot_from_rows(rows)
