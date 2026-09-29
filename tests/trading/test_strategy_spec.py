"""Natural-language gold specs stay inside the existing replay."""

from __future__ import annotations

import asyncio
import json

from mokli.agent.tools.propose_strategy import ProposeStrategyTool
from mokli.trading.backtest.engine import replay
from mokli.trading.strategy_lab import propose_strategy, request_live, save_strategy, start_paper
from mokli.trading.strategy_spec import spec_from_description
from mokli.trading.types import Candle

_EXAMPLE = (
    "أنشئ لي خوارزمية للذهب تعتمد على كسر قمة الساعة السابقة، "
    "مع تأكيد الاتجاه على الأربع ساعات، وقف خسارة خلف آخر قاع، ومخاطرة 1%."
)


def _rising(count: int = 80) -> list[Candle]:
    rows: list[Candle] = []
    price = 2300.0
    for index in range(count):
        price += 0.35
        rows.append(
            Candle(
                time_ms=index,
                open=price - 0.1,
                high=price + 0.15,
                low=price - 0.45,
                close=price,
            )
        )
    return rows


def test_example_description_becomes_a_checked_spec() -> None:
    spec = spec_from_description(_EXAMPLE, name="gold_hour_break")
    assert spec["logic_ok"] is True
    assert spec["instrument"] == "XAUUSD"
    assert spec["entry"] == "break_prior_high"
    assert spec["stop"] == "last_swing_low"
    assert spec["confirm_timeframe"] == "4h"
    assert spec["risk_percent"] == 1.0
    assert spec["version"] == 1


def test_free_code_is_refused() -> None:
    spec = spec_from_description("gold ```\nexec(open('x').read())\n``` risk 1%", name="bad")
    assert "free_code_refused" in spec["logic_errors"]
    assert spec["logic_ok"] is False


def test_spec_replays_on_the_existing_engine_and_stays_unexecuted(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("mokli.trading.strategy_lab.get_data_dir", lambda: tmp_path)
    monkeypatch.setattr("mokli.trading.paper._LEDGER", tmp_path / "paper_ledger.jsonl")
    candles = _rising()
    proposal = propose_strategy("gold_hour_break", candles, description=_EXAMPLE)
    assert proposal["executed"] is False
    assert proposal["broker_order"] is False
    assert proposal["status"] == "proposed"
    backtest = proposal["backtest"]
    assert isinstance(backtest, dict)
    assert backtest["ok"] is True
    assert backtest["strategy"] == "gold_hour_break"
    assert backtest["rs"]
    saved = save_strategy(proposal)
    assert saved["ok"] is True
    paper = start_paper(str(saved["id"]))
    assert paper["ok"] is True
    assert paper["executed"] is False
    refused = request_live(str(saved["id"]), approved=False)
    assert refused["reason"] == "live_requires_explicit_approval"
    assert refused["broker_order"] is False
    recorded = request_live(str(saved["id"]), approved=True)
    assert recorded["executed"] is False
    assert recorded["broker_order"] is False
    assert recorded["reason"] == "approval_recorded_no_broker_order"


def test_atr_replay_without_rules_is_unchanged() -> None:
    card = replay(_rising(40))
    assert card["strategy"] == "atr_breakout"


def test_incomplete_description_does_not_backtest() -> None:
    proposal = propose_strategy("partial", _rising(), description="استراتيجية للذهب")
    assert proposal["status"] == "invalid"
    assert proposal["executed"] is False
    assert proposal["program"] is None


def test_tool_propose_save_paper_and_live_refusal(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("mokli.trading.strategy_lab.get_data_dir", lambda: tmp_path)
    monkeypatch.setattr("mokli.trading.paper._LEDGER", tmp_path / "paper_ledger.jsonl")
    tool = ProposeStrategyTool()
    raw = asyncio.run(
        tool.execute(
            name="gold_hour_break",
            candles_json=json.dumps(
                [
                    {
                        "time_ms": candle.time_ms,
                        "open": candle.open,
                        "high": candle.high,
                        "low": candle.low,
                        "close": candle.close,
                    }
                    for candle in _rising()
                ]
            ),
            description=_EXAMPLE,
            action="save",
        )
    )
    payload = json.loads(raw)
    assert payload["saved"]["ok"] is True
    strategy_id = payload["saved"]["id"]
    paper = json.loads(asyncio.run(tool.execute(name="gold_hour_break", action="paper", strategy_id=strategy_id)))
    assert paper["run_state"] == "paper"
    live = json.loads(
        asyncio.run(
            tool.execute(
                name="gold_hour_break",
                action="activate",
                strategy_id=strategy_id,
                approve_live=False,
            )
        )
    )
    assert live["broker_order"] is False

