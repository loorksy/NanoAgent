"""The decision model receives evidence JSON that still parses."""

from __future__ import annotations

import json

import pytest
import tiktoken

from mokli.trading.agents.evidence import evidence_json_for_model
from mokli.trading.tool_errors import model_json


def test_evidence_json_drops_separator_space_only() -> None:
    payload = {
        "evidenceLevels": [round(2290.0 + i * 0.5, 2) for i in range(27)],
        "candidates": [{"id": f"c{i}", "action": "wait", "score": 0.1 * i} for i in range(8)],
        "teamBriefing": "- technical: range\nSTANCE: wait",
        "geometry": {"gaps": [{"low": 2298.5, "high": 2302.0} for _ in range(8)]},
    }
    loose = json.dumps(payload, ensure_ascii=False, default=str)
    tight = evidence_json_for_model(payload)
    assert json.loads(loose) == json.loads(tight)
    enc = tiktoken.get_encoding("cl100k_base")
    before = len(enc.encode(loose))
    after = len(enc.encode(tight))
    assert after < before
    assert before - after >= 50


def test_short_evidence_is_unchanged() -> None:
    payload = {
        "evidenceLevels": [2290.0, 2300.0],
        "candidates": [{"id": "c1", "action": "wait"}],
        "teamBriefing": "- technical: range\nSTANCE: wait",
    }
    assert evidence_json_for_model(payload) == model_json(payload)


def test_long_team_brief_stays_valid_json() -> None:
    narrative = "\n".join(
        f"- role{index}: " + ("detail " * 500) + f"\nSTANCE: {'buy' if index % 2 == 0 else 'sell'}"
        for index in range(6)
    )
    macro = json.dumps(
        {
            "macroDrivers": [
                {"driver": f"d{index}", "bias": "neutral", "one_line_rationale": "yields"}
                for index in range(4)
            ]
        },
        ensure_ascii=False,
    )
    briefing = narrative + "\n" + macro
    payload = {
        "evidenceLevels": [2290.0, 2300.0],
        "candidates": [{"id": "c1"}],
        "teamBriefing": briefing,
    }
    sliced = json.dumps(payload, ensure_ascii=False)[:18000]
    with pytest.raises(json.JSONDecodeError):
        json.loads(sliced)

    text = evidence_json_for_model(payload)
    parsed = json.loads(text)
    assert len(text) <= 18000
    assert parsed["evidenceLevels"] == [2290.0, 2300.0]
    assert parsed["candidates"] == [{"id": "c1"}]
    assert "STANCE: buy" in parsed["teamBriefing"]
    assert "STANCE: sell" in parsed["teamBriefing"]
    assert "macroDrivers" in parsed["teamBriefing"]
    assert len(parsed["teamBriefing"]) < len(briefing)
    assert payload["teamBriefing"] == briefing


def test_oversized_field_other_than_the_brief_is_not_sliced() -> None:
    payload = {"notes": "n" * 20000}
    text = evidence_json_for_model(payload, limit=18000)
    assert text == model_json(payload)
    assert len(text) > 18000
    assert json.loads(text)["notes"] == payload["notes"]
