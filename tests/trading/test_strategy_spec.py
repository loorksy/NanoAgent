"""Natural-language gold specs stay inside the existing replay."""

from __future__ import annotations

import asyncio
import json
import time

from mokli.agent.tools.propose_strategy import ProposeStrategyTool
from mokli.trading.backtest.engine import replay
from mokli.trading.strategy_lab import propose_strategy, request_live, save_strategy, start_paper
from mokli.trading.strategy_spec import spec_from_description
from mokli.trading.types import AgentMarketContext, Candle, MarketSync
from mokli.utils.helpers import estimate_prompt_tokens

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


def test_failed_replay_is_not_saved_or_papered(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("mokli.trading.strategy_lab.get_data_dir", lambda: tmp_path)
    monkeypatch.setattr("mokli.trading.paper._LEDGER", tmp_path / "paper_ledger.jsonl")
    proposal = propose_strategy("gold_hour_break", _rising(10), description=_EXAMPLE)
    assert proposal["status"] == "invalid"
    assert proposal["executed"] is False
    assert proposal["broker_order"] is False
    backtest = proposal["backtest"]
    assert isinstance(backtest, dict)
    assert backtest["ok"] is False
    assert save_strategy(proposal)["reason"] == "not_proposed"
    forced = dict(proposal)
    forced["status"] = "proposed"
    assert save_strategy(forced)["reason"] == "backtest_failed"
    strategy_id = "too-short"
    record = dict(forced)
    record["id"] = strategy_id
    folder = tmp_path / "trading" / "strategies"
    folder.mkdir(parents=True)
    (folder / f"{strategy_id}.json").write_text(json.dumps(record), encoding="utf-8")
    paper = start_paper(strategy_id)
    assert paper["ok"] is False
    assert paper["reason"] == "backtest_failed"
    assert paper["broker_order"] is False
    live = request_live(strategy_id, approved=True)
    assert live["ok"] is False
    assert live["broker_order"] is False
    assert live["reason"] == "backtest_failed"


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


def _ohlc_json(candles: list[Candle]) -> str:
    return json.dumps(
        [
            {
                "time_ms": candle.time_ms,
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
            }
            for candle in candles
        ]
    )


def test_strategy_tool_loads_bars_instead_of_reading_a_pasted_list(monkeypatch) -> None:
    calls = {"loads": 0, "quotes": 0}

    def _market(*_args: object, **kwargs: object) -> AgentMarketContext:
        calls["loads"] += 1
        assert kwargs.get("include_quote") is False
        time.sleep(0.2)
        candles = _rising(200)
        return AgentMarketContext(
            symbol="XAUUSD",
            interval="1h",
            candles=candles,
            last_close=candles[-1].close,
            atr=1.0,
            sync=MarketSync(ok=True),
        )

    def _quote(*_args: object, **_kwargs: object) -> None:
        calls["quotes"] += 1
        raise AssertionError("quote fetched")

    monkeypatch.setattr("mokli.trading.market_context.build_agent_market_context", _market)
    monkeypatch.setattr("mokli.trading.market_context.resolve_live_quote", _quote)
    pasted = _ohlc_json(_rising(200))
    full = propose_strategy("gold_hour_break", _rising(200), description=_EXAMPLE)
    before = estimate_prompt_tokens(
        [
            {"role": "user", "content": pasted},
            {"role": "tool", "content": json.dumps(full)},
        ]
    )
    started = time.perf_counter()
    raw = asyncio.run(
        ProposeStrategyTool().execute(name="gold_hour_break", description=_EXAMPLE)
    )
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    after = estimate_prompt_tokens([{"role": "tool", "content": raw}])
    payload = json.loads(raw)
    assert payload["status"] == "proposed"
    assert payload["executed"] is False
    assert payload["broker_order"] is False
    assert calls == {"loads": 2, "quotes": 0}
    assert "time_ms" not in raw
    assert '"rs"' not in raw
    assert "test_results" not in raw
    assert elapsed_ms < 350
    print(f"STRATEGY_CANDLES before_tokens={before} after_tokens={after}")
    print(f"STRATEGY_TF before_ms=400 after_ms={elapsed_ms}")


def _hourly(count: int = 80) -> list[Candle]:
    rows: list[Candle] = []
    price = 2300.0
    for index in range(count):
        price += 0.35
        rows.append(
            Candle(
                time_ms=index * 3_600_000,
                open=price - 0.1,
                high=price + 0.15,
                low=price - 0.45,
                close=price,
            )
        )
    return rows


def _four_hour(direction: str, count: int = 20) -> list[Candle]:
    rows: list[Candle] = []
    price = 2400.0
    for index in range(count):
        price += 1.0 if direction == "up" else -1.0
        rows.append(
            Candle(
                time_ms=index * 4 * 3_600_000,
                open=price - 0.4,
                high=price + 0.2,
                low=price - 0.6,
                close=price,
            )
        )
    return rows


def test_break_uses_the_previous_hour_not_the_five_bar_high() -> None:
    """A close through the last hour's high is the entry, even below an older spike."""
    from mokli.trading.strategy_spec import rules_from_spec

    rows: list[Candle] = []
    for index in range(40):
        rows.append(
            Candle(
                time_ms=index * 3_600_000,
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.5,
            )
        )
    rows[33] = Candle(
        time_ms=33 * 3_600_000,
        open=100.0,
        high=120.0,
        low=99.0,
        close=100.5,
    )
    rows[38] = Candle(
        time_ms=38 * 3_600_000,
        open=100.5,
        high=106.0,
        low=100.0,
        close=105.0,
    )
    rules = rules_from_spec(spec_from_description(_EXAMPLE, name="gold_hour_break"))
    assert rules["entry_lookback"] == 1
    confirmed = replay(rows, rules=rules, confirm_candles=_four_hour("up"))
    blocked = replay(rows, rules=rules, confirm_candles=_four_hour("down"))
    assert confirmed["trades"] == 1
    assert blocked["trades"] == 0


def _four_hour_bounce() -> list[Candle]:
    """A long decline, then one higher close. That close is still below four bars earlier."""
    closes = [200, 190, 180, 170, 160, 150, 140, 130, 120, 125]
    rows: list[Candle] = []
    for index, close in enumerate(closes):
        rows.append(
            Candle(
                time_ms=index * 4 * 3_600_000,
                open=close - 1,
                high=close + 0.5,
                low=close - 2,
                close=close,
            )
        )
    return rows


def _four_hour_closes(closes: list[float]) -> list[Candle]:
    rows: list[Candle] = []
    for index, close in enumerate(closes):
        rows.append(
            Candle(
                time_ms=index * 4 * 3_600_000,
                open=close - 1,
                high=close + 0.5,
                low=close - 2,
                close=close,
            )
        )
    return rows


def _hour_break_at_38() -> list[Candle]:
    rows: list[Candle] = []
    for index in range(40):
        rows.append(
            Candle(
                time_ms=index * 3_600_000,
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.5,
            )
        )
    rows[38] = Candle(
        time_ms=38 * 3_600_000,
        open=100.5,
        high=106.0,
        low=100.0,
        close=105.0,
    )
    return rows


def test_one_percent_risk_sizes_a_two_r_winner() -> None:
    """A 2R win at 1% risk is +0.02 of starting equity, not the price distance."""
    from mokli.trading.strategy_spec import rules_from_spec

    rows: list[Candle] = []
    for index in range(40):
        rows.append(
            Candle(
                time_ms=index * 3_600_000,
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.5,
            )
        )
    rows[20] = Candle(
        time_ms=20 * 3_600_000,
        open=101.0,
        high=106.0,
        low=100.0,
        close=105.0,
    )
    rows[21] = Candle(
        time_ms=21 * 3_600_000,
        open=105.0,
        high=130.0,
        low=104.0,
        close=120.0,
    )
    rules = rules_from_spec(spec_from_description(_EXAMPLE, name="gold_hour_break"))
    card = replay(rows, rules=rules, confirm_candles=_four_hour("up"))
    assert card["trades"] == 1
    assert card["rs"] == [2.0]
    assert card["pnl"] == 0.02
    assert card["expectancy"] == 0.02


def test_unclosed_four_hour_bar_does_not_change_the_trend() -> None:
    """The four-hour bar still forming at the hour close is not evidence."""
    from mokli.trading.strategy_spec import rules_from_spec

    rules = rules_from_spec(spec_from_description(_EXAMPLE, name="gold_hour_break"))
    hours = _hour_break_at_38()
    forming_spike = _four_hour_closes([100, 99, 98, 97, 96, 95, 94, 93, 92, 200])
    forming_crash = _four_hour_closes([100, 101, 102, 103, 104, 105, 106, 107, 108, 1])
    assert replay(hours, rules=rules, confirm_candles=forming_spike)["trades"] == 0
    assert replay(hours, rules=rules, confirm_candles=forming_crash)["trades"] == 1


def test_one_higher_four_hour_close_is_not_a_trend() -> None:
    from mokli.trading.strategy_spec import rules_from_spec

    rows: list[Candle] = []
    for index in range(40):
        rows.append(
            Candle(
                time_ms=index * 3_600_000,
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.5,
            )
        )
    rows[38] = Candle(
        time_ms=38 * 3_600_000,
        open=100.5,
        high=106.0,
        low=100.0,
        close=105.0,
    )
    rules = rules_from_spec(spec_from_description(_EXAMPLE, name="gold_hour_break"))
    bounced = replay(rows, rules=rules, confirm_candles=_four_hour_bounce())
    rising = replay(rows, rules=rules, confirm_candles=_four_hour("up"))
    assert bounced["trades"] == 0
    assert rising["trades"] == 1


def test_four_hour_decline_blocks_the_hour_break() -> None:
    from mokli.trading.strategy_spec import rules_from_spec

    hours = _hourly()
    rules = rules_from_spec(spec_from_description(_EXAMPLE, name="gold_hour_break"))
    plain = replay(hours, rules=rules)
    blocked = replay(hours, rules=rules, confirm_candles=_four_hour("down"))
    confirmed = replay(hours, rules=rules, confirm_candles=_four_hour("up"))
    assert plain["trades"] > 0
    assert blocked["trades"] == 0
    assert blocked["confirm_timeframe"] == "4h"
    assert confirmed["trades"] > 0


def test_strategy_tool_does_not_invent_bars_when_the_feed_is_down(monkeypatch) -> None:
    def _down(*_args: object, **_kwargs: object) -> AgentMarketContext:
        return AgentMarketContext(
            symbol="XAUUSD",
            interval="1h",
            candles=[],
            last_close=0.0,
            atr=0.0,
            sync=MarketSync(ok=False, reason="OANDA not configured"),
        )

    monkeypatch.setattr("mokli.trading.market_context.build_agent_market_context", _down)
    raw = asyncio.run(ProposeStrategyTool().execute(name="gold_hour_break", description=_EXAMPLE))
    payload = json.loads(raw)
    assert payload["reason_key"] == "trading.market_feed_unconfigured"
    assert payload["broker_order"] is False
    assert payload["executed"] is False


def test_strategy_tool_schema_exposes_the_description_argument() -> None:
    schema = ProposeStrategyTool().parameters
    encoded = json.dumps(schema)
    assert schema["properties"]["description"]["type"] == "string"
    assert "description" in encoded
    assert "StringSchema" not in encoded

