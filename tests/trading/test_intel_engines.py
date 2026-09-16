"""Unit tests for FEATURE engines that must work without paid extras."""

from __future__ import annotations

import pytest

from nanobot.trading.intel.calendar_scraper import parse_calendar_json
from nanobot.trading.intel.dtw_matcher import match_pattern
from nanobot.trading.intel.intermarket import divergence_matrix, intermarket_snapshot
from nanobot.trading.intel.local_sentiment import classify_sentiment
from nanobot.trading.intel.postmortem import LossRecord, PostMortemLog
from nanobot.trading.intel.regex_emergency import scan_emergency
from nanobot.trading.intel.rss_aggregator import parse_feed_body, reset_seen_for_tests
from nanobot.trading.intel.telegram_scraper import TelegramHeadlineSource
from nanobot.trading.intel.vector_playbook import VectorPlaybook
from nanobot.trading.intel.vip_tracker import _impact
from nanobot.trading.risk_state import RiskStateStore


def test_regex_emergency_war_and_lock(tmp_path, monkeypatch):
    store = RiskStateStore(tmp_path / "risk.json")
    monkeypatch.setattr("nanobot.trading.intel.regex_emergency.get_risk_store", lambda: store)
    hit = scan_emergency("Missile strike on a major city", apply_lock=True)
    assert hit.matched is True
    assert hit.freeze is True
    assert store.snapshot().emergency_lock is True
    assert scan_emergency("quiet session").matched is False


def test_vector_playbook_ranks_similar_context():
    book = VectorPlaybook()
    matches = book.query("asian high false break M15 structure weak dollar")
    assert matches
    assert matches[0].score >= matches[-1].score


def test_dtw_picks_a_template():
    series = [0.4, 0.41, 0.42, 0.43, 0.42, 0.45, 0.46, 0.5, 0.54, 0.58]
    match = match_pattern(series)
    assert match.name in {"accumulation", "distribution", "turtle_soup", "v_reversal"}
    assert 0.0 <= match.confidence <= 1.0


def test_postmortem_repeat_detection(tmp_path):
    log = PostMortemLog(tmp_path / "pm.sqlite")
    rec = LossRecord(2650, 2640, 1, "dxy_up", "asia_sweep", 18.0, "early_entry", "buy")
    log.record(rec)
    log.record(rec)
    log.record(rec)
    found = log.repeats_recent_error(setup="asia_sweep", dxy_state="dxy_up", side="buy")
    assert found is not None
    assert log.repeats_recent_error(setup="other", dxy_state="dxy_up", side="buy") is None


def test_calendar_json_surprise():
    rows = parse_calendar_json(
        [{"title": "NFP", "currency": "USD", "impact": "high", "forecast": "200", "actual": "250"}]
    )
    assert rows[0].surprise == 50.0


def test_intermarket_divergence_and_override():
    snap = intermarket_snapshot({"dxy": 104.0, "xau": 2650.0})
    assert snap.prices["dxy"] == 104.0
    matrix = divergence_matrix({"dxy": 103.0, "xau": 2640.0}, {"dxy": 104.0, "xau": 2650.0})
    assert matrix["gold_bullish_vs_dxy"] is True


@pytest.mark.asyncio
async def test_sentiment_fallback_hawkish():
    result = await classify_sentiment("The Fed remains restrictive with another hike likely.")
    assert result.bias == "BEARISH_GOLD"
    assert result.source in {"fallback", "ollama"}


def test_telegram_probe_without_credentials():
    src = TelegramHeadlineSource(api_id=0, api_hash="")
    assert src.configured() is False
    assert src.available() is False


def test_rss_parse_feed_body_without_network():
    pytest.importorskip("feedparser")
    reset_seen_for_tests()
    xml = """<?xml version="1.0"?><rss version="2.0"><channel>
    <title>Fed</title>
    <item><title>FOMC holds rates</title><guid>g-1</guid><link>https://example.test/1</link></item>
    </channel></rss>"""
    rows = parse_feed_body("https://example.test/feed", xml)
    assert rows
    assert "FOMC" in rows[0].title


def test_vip_impact_marks_fed_high():
    assert _impact("federalreserve") == "high"
    assert _impact("randomhandle") == "medium"
