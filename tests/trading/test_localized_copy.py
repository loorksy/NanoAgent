"""User-facing copy in trading helpers resolves through the locale catalog."""

from __future__ import annotations

import re

import pytest

from mokli.trading.agents.visual_capture import capture_visual_evidence
from mokli.trading.i18n import tr
from mokli.trading.recommendations import followup
from mokli.trading.recommendations.tradability import assess_plan_tradability
from mokli.trading.types import AgentRecommendation, FinalDecisionResult

_ARABIC = re.compile(r"[\u0600-\u06FF]")


@pytest.mark.parametrize("locale", ["en", "ar"])
async def test_visual_capture_notes_follow_locale(locale: str) -> None:
    visual, _snapshots = await capture_visual_evidence("15m", capture=None, locale=locale)
    assert visual.notes == tr("visual.no_snapshot", locale)

    async def _boom(_timeframes: list[str]) -> dict:
        raise RuntimeError("offline")

    visual, _snapshots = await capture_visual_evidence("15m", capture=_boom, locale=locale)
    assert visual.notes == tr("visual.capture_failed", locale, error="offline")
    assert bool(_ARABIC.search(visual.notes)) == (locale == "ar")


async def test_visual_capture_partial_and_full_notes() -> None:
    async def _partial(_timeframes: list[str]) -> dict:
        return {"frames": [{"timeframe": "15m", "image": "x"}]}

    visual, _snapshots = await capture_visual_evidence("15m", capture=_partial, locale="en")
    assert visual.state in {"partial", "checked"}
    if visual.state == "partial":
        assert visual.notes == tr(
            "visual.partial", "en", shown="15m", missing=", ".join(visual.missing)
        )
    else:
        assert visual.notes == tr("visual.read_charts", "en", shown="15m")


def test_explain_stored_recommendation_is_localized(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(followup, "get_recommendation", lambda _rec_id: None)
    assert followup.explain_stored_recommendation("x", "ar") == tr("followup.stored_not_found", "ar")
    row = {
        "direction": "buy",
        "entry": 2400.0,
        "stop_loss": 2390.0,
        "targets": [2420.0],
        "summary": "s",
    }
    monkeypatch.setattr(followup, "get_recommendation", lambda _rec_id: row)
    text = followup.explain_stored_recommendation("x", "ar")
    assert tr("followup.stored_headline", "ar", direction="BUY", summary="s") in text
    assert _ARABIC.search(text)
    text_en = followup.explain_stored_recommendation("x")
    assert "Entry: 2400.0" in text_en and "Targets: 2420.0" in text_en


def test_grade_live_recommendation_without_row_uses_catalog() -> None:
    result = followup.grade_live_recommendation(None, operator_text="متابعة")
    assert result.refusal_summary == tr("followup.no_live_plan_reason", "ar")
    assert result.key_reasons == [tr("followup.no_live_plan_reason", "ar")]


def test_tradability_reasons_are_machine_keys() -> None:
    wait = FinalDecisionResult(
        decision="wait",
        confidence=0.1,
        summary="",
        key_reasons=[],
        risk_warnings=[],
        recommendation=AgentRecommendation(action="wait"),
    )
    ok, reason = assess_plan_tradability(wait)
    assert (ok, reason) == (False, "wait_decision")
    assert re.fullmatch(r"[a-z_]+", reason)
