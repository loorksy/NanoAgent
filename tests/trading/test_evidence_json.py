"""The decision model receives evidence JSON that still parses."""

from __future__ import annotations

import json

import pytest

from mokli.trading.agents.evidence import evidence_json_for_model


def test_short_evidence_is_unchanged() -> None:
    payload = {
        "evidenceLevels": [2290.0, 2300.0],
        "candidates": [{"id": "c1", "action": "wait"}],
        "teamBriefing": "- technical: range\nSTANCE: wait",
    }
    assert evidence_json_for_model(payload) == json.dumps(payload, ensure_ascii=False, default=str)


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
    assert text == json.dumps(payload, ensure_ascii=False, default=str)
    assert len(text) > 18000
    assert json.loads(text)["notes"] == payload["notes"]
