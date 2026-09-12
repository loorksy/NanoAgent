import json
from pathlib import Path

from nanobot.trading.memory.decisions import (
    format_decisions_for_dream,
    list_recent_decisions,
    record_trade_decision,
    trades_memory_path,
)
from nanobot.trading.types import (
    AgentMarketContext,
    AgentRecommendation,
    FinalDecisionResult,
    MarketSync,
)


def test_record_and_list_decisions(tmp_path, monkeypatch) -> None:
    path = tmp_path / "trading" / "trades.jsonl"
    monkeypatch.setattr(
        "nanobot.trading.memory.decisions._TRADES_PATH",
        path,
    )
    decision = FinalDecisionResult(
        decision="buy",
        confidence=0.8,
        summary="Test setup",
        key_reasons=["structure"],
        risk_warnings=[],
        recommendation=AgentRecommendation(
            action="buy",
            symbol="XAUUSD",
            interval="15m",
            entry=2400.0,
            stop_loss=2390.0,
            targets=[2410.0],
            execution_state="valid_now",
        ),
    )
    market = AgentMarketContext(
        symbol="XAUUSD",
        interval="15m",
        candles=[],
        last_close=2400.0,
        atr=5.0,
        sync=MarketSync(ok=True),
        quote_mid=2400.0,
    )
    record_trade_decision("rec-1", decision, market)
    rows = list_recent_decisions()
    assert len(rows) == 1
    assert rows[0]["direction"] == "buy"
    block = format_decisions_for_dream()
    assert "trades.jsonl" in block
    assert "Test setup" in block
