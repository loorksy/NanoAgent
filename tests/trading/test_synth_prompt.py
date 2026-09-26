"""The decision contract's JSON schema must round-trip through the synthesizer parser."""

from __future__ import annotations

import json
import re

from mokli.agent.prompt.composer import decision_contract_template
from mokli.trading.agents.apply_model_decision import apply_model_decision
from mokli.trading.agents.synth_prompt import SYNTH_SYSTEM_PROMPT, synth_system_prompt
from mokli.trading.agents.synthesizer import _extract_json
from mokli.trading.types import EvidenceSnapshot

ARABIC_RE = re.compile(r"[\u0600-\u06FF]")

EXPECTED_KEYS = {
    "direction",
    "planType",
    "selectedTradeCandidateId",
    "proposedLevels",
    "timeframeRoles",
    "activationCondition",
    "activationRule",
    "invalidationRule",
    "alternativeScenario",
    "validityCandles",
    "confidence",
    "summary",
    "keyReasons",
    "riskWarnings",
    "publicReasoningSummary",
    "decisionTrace",
    "drawingAdvice",
    "selectedCandidateIds",
    "scenarioPath",
    "alternativeScenarioPath",
    "artifactsRequested",
    "browse",
}


def _schema_line() -> str:
    lines = [line for line in SYNTH_SYSTEM_PROMPT.splitlines() if line.startswith('{"direction"')]
    assert len(lines) == 1
    return lines[0]


def _snapshot() -> EvidenceSnapshot:
    return EvidenceSnapshot(
        payload={
            "candidates": [
                {
                    "id": "cand-bull-1",
                    "action": "buy",
                    "entry": 4300.0,
                    "stopLoss": 4290.0,
                    "targets": [4315.0, 4330.0],
                    "entryType": "market",
                }
            ],
            "mtf": {"current_bias": "bullish", "conflict": False},
            "structure": {"trend": "uptrend"},
        },
        evidence_levels=[4290.0, 4300.0, 4315.0, 4330.0],
    )


def test_schema_line_is_valid_json_with_the_parsed_keys() -> None:
    schema = json.loads(_schema_line())
    assert set(schema) == EXPECTED_KEYS
    assert set(schema["timeframeRoles"]) == {"lead", "context", "timing"}
    assert set(schema["decisionTrace"]) == {"hypotheses", "chosenBecause", "planTypeBecause"}
    assert set(schema["scenarioPath"][0]) == {"barsAhead", "price", "label"}


def test_sample_decision_round_trips_through_parser_and_coercions() -> None:
    sample = json.loads(_schema_line())
    sample.update(
        {
            "direction": "buy",
            "planType": "immediate",
            "selectedTradeCandidateId": "cand-bull-1",
            "invalidationRule": "Close below the demand zone",
            "alternativeScenario": "Sweep of the low first",
            "confidence": 0.72,
            "summary": "Gold long from demand",
            "keyReasons": ["structure", "liquidity"],
            "riskWarnings": ["news window"],
            "publicReasoningSummary": ["bias up"],
            "decisionTrace": {
                "hypotheses": [{"scenario": "continuation", "supporting": ["bos"], "opposing": []}],
                "chosenBecause": "trend",
                "planTypeBecause": "inside zone",
            },
            "scenarioPath": [
                {"barsAhead": 2, "price": 4305.0, "label": "pullback"},
                {"barsAhead": 6, "price": 4330.0, "label": "target"},
            ],
            "alternativeScenarioPath": [
                {"barsAhead": 3, "price": 4295.0, "label": "sweep"},
                {"barsAhead": 5, "price": 4290.0, "label": "stop"},
            ],
            "artifactsRequested": ["decision", "level_map"],
        }
    )
    raw = "```json\n" + json.dumps(sample) + "\n```"
    parsed = _extract_json(raw)
    assert parsed == sample

    result = apply_model_decision(
        parsed,
        snapshot=_snapshot(),
        live_price=4301.0,
        atr=5.0,
        interval="15m",
        locale="en",
    )
    assert result.decision == "buy"
    assert result.plan_type == "immediate"
    assert result.recommendation.entry == 4300.0
    assert result.recommendation.targets[:1] == [4315.0]
    assert result.recommendation.timeframe_roles.lead == "15m"
    assert result.recommendation.decision_trace.chosen_because == "trend"
    assert "decision" in result.artifacts_requested
    assert result.summary == "Gold long from demand"


def test_exported_symbols_and_language_rendering() -> None:
    assert SYNTH_SYSTEM_PROMPT == decision_contract_template()
    assert "teamBriefing.macroDrivers" in SYNTH_SYSTEM_PROMPT
    assert "raise confidence" in SYNTH_SYSTEM_PROMPT
    ar = synth_system_prompt("ar")
    en = synth_system_prompt("en-US")
    auto = synth_system_prompt("")
    assert "in natural Arabic" in ar
    assert "in natural English" in en
    assert "in natural the operator's language" in auto
    for prompt in (ar, en, auto):
        assert "{language}" not in prompt
        assert "{product_name}" not in prompt
        assert "You are Mokli" in prompt
        assert "# Hard law" in prompt
        assert not ARABIC_RE.search(prompt)
        assert "lonora" not in prompt.lower()
    assert "You are GoldDesk" in synth_system_prompt("en", product_name="GoldDesk")


def test_contract_does_not_hard_code_thresholds() -> None:
    body = SYNTH_SYSTEM_PROMPT.split("Respond with ONLY a JSON object")[0]
    assert not re.search(r"\b\d+\s*[–-]\s*\d+\s+gold points", body)
    assert "configured follow-through tolerance" in body
