"""Keyword lexicons load from JSON data files, not Python literals."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from mokli.trading.agents import macro_drivers
from mokli.trading.intel import lexicon, local_sentiment, regex_emergency

LEXICON_DIR = Path("mokli/trading/intel/lexicon")

EXPECTED = {
    "macro_bullish",
    "macro_bearish",
    "hawkish",
    "dovish",
    "calendar_us_real_yields_fomc",
    "calendar_dxy",
    "calendar_us_macro_data",
    "emergency_war",
    "emergency_monetary",
    "emergency_sanctions",
}


def test_every_expected_lexicon_ships_as_json() -> None:
    assert EXPECTED <= set(lexicon.available())
    for name in EXPECTED:
        data = json.loads((LEXICON_DIR / f"{name}.json").read_text(encoding="utf-8"))
        assert isinstance(data, list) and data, name
        assert all(isinstance(item, str) and item == item.lower() for item in data), name
        assert len(set(data)) == len(data), f"duplicate phrase in {name}"


def test_load_returns_cached_frozenset() -> None:
    first = lexicon.load("hawkish")
    assert isinstance(first, frozenset)
    assert "hike" in first
    assert lexicon.load("hawkish") is first


def test_load_rejects_unknown_or_invalid_names() -> None:
    with pytest.raises(FileNotFoundError):
        lexicon.load("does_not_exist")
    with pytest.raises(ValueError):
        lexicon.load("../etc/passwd")


def test_alternation_matches_whole_phrases_case_insensitively() -> None:
    pattern = lexicon.alternation("emergency_war")
    assert isinstance(pattern, re.Pattern)
    assert pattern.search("Breaking: MISSILE strike reported")
    assert pattern.search("war declared overnight")
    assert not pattern.search("warm session, calm tape")


def test_macro_drivers_and_sentiment_consume_lexicon() -> None:
    assert macro_drivers.CALENDAR_KEYWORDS["dxy"] == lexicon.load("calendar_dxy")
    assert local_sentiment.HAWKISH == lexicon.load("hawkish")
    assert local_sentiment.DOVISH == lexicon.load("dovish")
    assert regex_emergency.WAR.pattern == lexicon.alternation("emergency_war").pattern
    bias, _strength = macro_drivers._bias_from_text("dovish fed, weaker dollar, inflows")
    assert bias == "bullish"
    bias, _strength = macro_drivers._bias_from_text("hawkish presser, stronger dollar, outflow")
    assert bias == "bearish"
