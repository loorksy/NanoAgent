"""Phase 3: macroDrivers must change synthesizer confidence inside the unified agent.

STOP A: before the documented adjustment rule, opposite briefings produced the
same confidence because teamBriefing was only dumped into evidence JSON.
"""

from __future__ import annotations

import json

import pytest

from mokli.trading.agents.apply_model_decision import (
    MACRO_CONFIDENCE_WEIGHT,
    apply_macro_confidence,
    apply_model_decision,
    macro_alignment_score,
    parse_macro_drivers,
)
from mokli.trading.agents.macro_drivers import format_team_briefing
from mokli.trading.agents.synth_prompt import SYNTH_SYSTEM_PROMPT
from mokli.trading.kernel import run_trading_kernel
from mokli.trading.types import (
    EvidenceSnapshot,
)


def _driver(name: str, bias: str, strength: int) -> dict:
    from mokli.trading.agents.macro_drivers import MacroVerdict

    return MacroVerdict(
        driver=name,
        bias=bias,
        strength=strength,
        one_line_rationale=f"{name} {bias}",
        source="Reuters",
        ran=True,
        reason="cache_miss",
    )


def _briefing(bias: str, strength: int = 80) -> str:
    return format_team_briefing(
        [
            _driver("dxy", bias, strength),
            _driver("geopolitical_safehaven", bias, strength),
            _driver("us_real_yields_fomc", bias, strength),
        ]
    )


def _fixed_model_json() -> str:
    return json.dumps(
        {
            "direction": "buy",
            "planType": "immediate",
            "selectedTradeCandidateId": "cand-bull-1",
            "proposedLevels": None,
            "confidence": 0.60,
            "summary": "Gold BUY from demand",
            "keyReasons": ["demand held"],
            "riskWarnings": [],
            "decisionTrace": {
                "hypotheses": [{"scenario": "buy", "supporting": ["demand"], "opposing": []}],
                "chosenBecause": "demand",
                "planTypeBecause": "inside zone",
            },
            "scenarioPath": [
                {"barsAhead": 2, "price": 2410, "label": "impulse"},
                {"barsAhead": 8, "price": 2440, "label": "target"},
            ],
            "alternativeScenarioPath": [
                {"barsAhead": 3, "price": 2392, "label": "fail"},
                {"barsAhead": 6, "price": 2385, "label": "stop"},
            ],
            "browse": None,
        }
    )


def _snapshot(briefing: str | None) -> EvidenceSnapshot:
    return EvidenceSnapshot(
        payload={
            "mtf": {"current_bias": "bullish", "conflict": False},
            "structure": {"trend": "uptrend"},
            "candidates": [
                {
                    "id": "cand-bull-1",
                    "action": "buy",
                    "entry": 2400.0,
                    "stopLoss": 2385.0,
                    "targets": [2420.0, 2440.0],
                    "entryType": "market",
                }
            ],
            "teamBriefing": briefing,
        },
        evidence_levels=[2385.0, 2400.0, 2420.0, 2440.0],
    )


def test_prompt_names_macro_briefing() -> None:
    assert "teamBriefing.macroDrivers" in SYNTH_SYSTEM_PROMPT
    assert "raise confidence" in SYNTH_SYSTEM_PROMPT


def test_opposite_briefings_change_apply_model_confidence() -> None:
    parsed = json.loads(_fixed_model_json())
    bull = apply_model_decision(
        parsed, snapshot=_snapshot(_briefing("bullish")), live_price=2400.0, atr=8.0, locale="en"
    )
    bear = apply_model_decision(
        parsed, snapshot=_snapshot(_briefing("bearish")), live_price=2400.0, atr=8.0, locale="en"
    )
    none = apply_model_decision(
        parsed, snapshot=_snapshot(None), live_price=2400.0, atr=8.0, locale="en"
    )
    # Same model JSON: side stays buy; confidence must move.
    assert bull.decision == bear.decision == "buy"
    assert none.confidence == pytest.approx(0.60)
    assert bull.confidence == pytest.approx(apply_macro_confidence(0.60, 1.0))
    assert bear.confidence == pytest.approx(apply_macro_confidence(0.60, -1.0))
    assert bull.confidence - bear.confidence == pytest.approx(2 * MACRO_CONFIDENCE_WEIGHT)
    assert any("Macro drivers" in reason for reason in bull.key_reasons)


def test_parse_and_alignment_helpers() -> None:
    drivers = parse_macro_drivers(_snapshot(_briefing("bearish")))
    assert len(drivers) == 3
    assert macro_alignment_score("buy", drivers) == pytest.approx(-1.0)
    assert macro_alignment_score("sell", drivers) == pytest.approx(1.0)


def test_swarm_notes_keep_the_trailing_driver_vote() -> None:
    """Role notes are not JSON. The driver line after them still votes."""
    from mokli.trading.teams.runtime import _format_swarm_briefing

    pure = _briefing("bearish")
    notes = _format_swarm_briefing(
        "gold_decision_review",
        {"task-technical": "range\nSTANCE: wait", "task-macro": "yields up\nSTANCE: sell"},
        pure,
    )
    assert not notes.strip().startswith("{")
    parsed = json.loads(_fixed_model_json())
    from_notes = apply_model_decision(
        parsed, snapshot=_snapshot(notes), live_price=2400.0, atr=8.0, locale="en"
    )
    from_json = apply_model_decision(
        parsed, snapshot=_snapshot(pure), live_price=2400.0, atr=8.0, locale="en"
    )
    assert parse_macro_drivers(_snapshot(notes)) == parse_macro_drivers(_snapshot(pure))
    assert from_notes.confidence == pytest.approx(from_json.confidence)
    assert from_notes.confidence == pytest.approx(apply_macro_confidence(0.60, -1.0))
    prose_only = _format_swarm_briefing(
        "gold_decision_review",
        {"task-technical": "range\nSTANCE: wait"},
        "",
    )
    assert parse_macro_drivers(_snapshot(prose_only)) == []


def _install_specialist_stubs(monkeypatch) -> None:
    from evidence_stubs import install_evidence_stubs

    install_evidence_stubs(monkeypatch)


@pytest.mark.asyncio
async def test_unified_agent_opposite_briefings_change_confidence(monkeypatch) -> None:
    _install_specialist_stubs(monkeypatch)
    seen: list[str] = []

    async def complete(messages):
        blob = json.dumps(messages, default=str)
        seen.append(blob)
        assert "teamBriefing" in blob
        assert "macroDrivers" in blob
        return _fixed_model_json()

    bull = await run_trading_kernel(
        store=False,
        team_briefing=_briefing("bullish"),
        complete=complete,
    )
    bear = await run_trading_kernel(
        store=False,
        team_briefing=_briefing("bearish"),
        complete=complete,
    )
    assert bull.decision.decision == "buy"
    assert bear.decision.decision == "buy"
    assert bull.decision.confidence > bear.decision.confidence
    assert bull.decision.confidence - bear.decision.confidence == pytest.approx(
        2 * MACRO_CONFIDENCE_WEIGHT
    )
    assert any("teamBriefing" in blob for blob in seen)
