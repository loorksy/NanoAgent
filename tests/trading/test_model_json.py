"""Model-facing trading JSON keeps every value and drops pretty-print space."""

from __future__ import annotations

import json

import tiktoken

from mokli.trading.tool_errors import model_json, tool_error
from mokli.trading.types import PriceLevel, StructureEvent, StructureResult, Swing
from mokli.trading.unified_evidence import _json_safe


def _structure_slice() -> dict[str, object]:
    swings = [
        Swing(
            type="high" if i % 2 == 0 else "low",
            time=1_700_000_000_000 + i * 900_000,
            price=round(2300.0 + i * 0.15, 2),
        )
        for i in range(80)
    ]
    support = [
        PriceLevel(price=round(2290.5 + i * 0.25, 2), time=1_700_000_000_000 + i * 900_000)
        for i in range(12)
    ]
    resistance = [
        PriceLevel(price=round(2400.5 + i * 0.25, 2), time=1_700_000_000_000 + i * 900_000)
        for i in range(12)
    ]
    event = StructureEvent(
        type="BOS",
        direction="bullish",
        broken_level=2340.5,
        break_candle_time=1_700_000_000_000,
        confirmation_close=2341.2,
        strength=0.82,
    )
    structure = StructureResult(
        trend="bullish",
        swings=swings,
        support=support,
        resistance=resistance,
        structure_events=[event, event, event],
        latest_structure_event=event,
    )
    safe = _json_safe(structure)
    assert isinstance(safe, dict)
    assert len(safe["swings"]) == 40
    return {"nodes": {"structure": safe}}


def test_structure_slice_drops_pretty_print_space_only() -> None:
    payload = _structure_slice()
    pretty = json.dumps(payload, indent=2, default=str)
    tight = model_json(payload)
    assert json.loads(pretty) == json.loads(tight)
    assert "\n" not in tight
    swings = json.loads(tight)["nodes"]["structure"]["swings"]
    assert len(swings) == 40
    assert swings[0]["price"] == 2300.0
    enc = tiktoken.get_encoding("cl100k_base")
    before = len(enc.encode(pretty))
    after = len(enc.encode(tight))
    print(f"EVIDENCE_JSON before={before} after={after}")
    assert after < before


def test_tool_error_stays_json_without_pretty_print() -> None:
    result = tool_error(
        "trading.no_live_quote",
        instruction="Read the quote again before deciding.",
        symbol="XAUUSD",
    )
    text = str(result)
    payload = json.loads(text)
    assert payload["ok"] is False
    assert payload["reason_key"] == "trading.no_live_quote"
    assert payload["symbol"] == "XAUUSD"
    assert "\n" not in text
