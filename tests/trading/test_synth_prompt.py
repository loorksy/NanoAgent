"""The decision contract's JSON schema must round-trip through the synthesizer parser."""

from __future__ import annotations

import asyncio
import json
import re

from mokli.agent.prompt.composer import compose_decision_prompt, decision_contract_template
from mokli.trading.agents.apply_model_decision import apply_model_decision
from mokli.trading.agents.synth_prompt import SYNTH_SYSTEM_PROMPT, synth_system_prompt
from mokli.trading.agents.synthesizer import _call_model, _extract_json
from mokli.trading.types import AgentMarketContext, Candle, EvidenceSnapshot, MarketSync
from mokli.utils.helpers import estimate_prompt_tokens

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


def _image_urls(messages: list[dict]) -> list[str]:
    found: list[str] = []
    for message in messages:
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if isinstance(part, dict) and part.get("type") == "image_url":
                found.append(str(part["image_url"]["url"]))
    return found


def test_followup_rounds_drop_chart_images() -> None:
    image = "data:image/png;base64," + ("A" * 8000)
    seen: list[list[dict]] = []

    async def complete(messages: list[dict]) -> str:
        seen.append(messages)
        if len(seen) == 1:
            return "not json"
        if len(seen) == 2:
            return '{"direction":"wait","browse":{"verb":"read_zone","low":1,"high":2}}'
        return '{"direction":"wait"}'

    market = AgentMarketContext(
        symbol="XAUUSD",
        interval="15m",
        candles=[Candle(time_ms=1, open=1, high=2, low=1, close=1.5)],
        last_close=1.5,
        atr=0.2,
        sync=MarketSync(ok=True),
    )
    parsed = asyncio.run(
        _call_model(
            snapshot=EvidenceSnapshot(payload={"candleCount": 1}),
            language="en",
            complete=complete,
            market=market,
            snapshots=[{"timeframe": "15m", "image": image, "context": "session high"}],
        )
    )
    assert parsed == {"direction": "wait"}
    assert _image_urls(seen[0]) == [image]
    assert _image_urls(seen[1]) == []
    assert _image_urls(seen[2]) == []
    followup = json.dumps(seen[2])
    assert image not in followup
    assert "CHART 15m" in followup
    assert len(json.dumps(seen[0])) > len(followup) + 7000


def test_contract_does_not_hard_code_thresholds() -> None:
    body = SYNTH_SYSTEM_PROMPT.split("Respond with ONLY a JSON object")[0]
    assert not re.search(r"\b\d+\s*[–-]\s*\d+\s+gold points", body)
    assert "configured follow-through tolerance" in body


def test_decision_contract_names_the_zone_and_calendar_fields() -> None:
    """The synthesizer payload has zone objects and news.upcoming, not a validation flag."""
    text = compose_decision_prompt(language="en")
    assert "zones.nearestDemand" in text
    assert "zones.nearestSupply" in text
    assert "no validation flag" in text
    assert "news.upcoming" in text
    assert "validated POI" not in text
    old = text.replace(
        "5. Re-check the plan against executionCost and news.upcoming before you answer. If news.upcoming is missing or empty, do not invent a release.",
        "5. Re-check the plan against the costs and the calendar before you answer.",
    )
    old = old.replace(
        "1. Is the current price INSIDE zones.nearestDemand or zones.nearestSupply for my direction, with acceptable net cost, and does this evidence already say that zone was tested?",
        "1. Is the current price INSIDE a validated POI/zone for my direction, with acceptable net cost?",
    )
    old = old.replace(
        "- F. News window, only when news.upcoming names that window",
        "- F. News window",
    )
    old = old.replace(
        "- zones.nearestDemand and zones.nearestSupply are the only supply and demand objects. Each has type, low, high, and time. There is no validation flag. Do not invent a zone those objects do not contain.\n"
        "- news.upcoming is the calendar. Each item has title, time, impact, and currency. An empty list is not a prompt to invent a session or a news window.\n",
        "",
    )
    before = estimate_prompt_tokens([{"role": "user", "content": old}])
    after = estimate_prompt_tokens([{"role": "user", "content": text}])
    print(f"DECISION_FIELDS before={before} after={after}")
    assert "validated POI" in old
    assert before < after
