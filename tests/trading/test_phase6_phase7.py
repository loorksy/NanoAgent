"""Phase 6 and 7 behaviour: management, pending orders, warehouse, backtest, scenarios."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from nanobot.trading.backtest.engine import replay
from nanobot.trading.delivery import broadcast_channels, silence_blocks
from nanobot.trading.gates.max_positions import evaluate_max_total_lots
from nanobot.trading.gates.risk_snapshot import RiskSnapshot
from nanobot.trading.geometry.detectors import momentum_is_weak, momentum_score
from nanobot.trading.management.engine import ManagedPosition, plan_position_actions
from nanobot.trading.mt5_execution import mt5_confirm_order, mt5_propose_order
from nanobot.trading.mt5_metaapi import NullTransport, set_transport_for_tests
from nanobot.trading.oanda_stream import feed_health, note_tick
from nanobot.trading.reports.behaviour import postmortem_artifact, record_daily_wrap_answer
from nanobot.trading.reports.scorecard import build_scorecard
from nanobot.trading.scenarios.trigger_engine import ScenarioSpec, ScenarioWatch
from nanobot.trading.types import Candle
from nanobot.trading.warehouse import CandleWarehouse

SAFE_TS = datetime(2023, 11, 15, 12, 0, tzinfo=UTC).timestamp()


def _candle(close: float, *, volume: float, up: bool) -> Candle:
    open_ = close - 1 if up else close + 1
    return Candle(
        time_ms=1,
        open=open_,
        high=max(open_, close) + 0.2,
        low=min(open_, close) - 0.2,
        close=close,
        volume=volume,
    )


def test_momentum_score_uses_tick_volume() -> None:
    quiet = [_candle(100 + i, volume=10, up=True) for i in range(5)]
    loud = quiet + [_candle(110, volume=40, up=True)]
    assert momentum_score(loud) > momentum_score(quiet)
    weak = [_candle(100, volume=10, up=False), _candle(99, volume=1, up=False)]
    assert momentum_is_weak(weak, direction="buy") is True


def test_max_total_lots_vetoes_aggregate_exposure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "nanobot.trading.gates.max_positions.live",
        lambda: type("P", (), {"MAX_TOTAL_LOTS": 1.0})(),
    )
    blocked = evaluate_max_total_lots(RiskSnapshot(open_lots=0.8, proposed_lot=0.4))
    assert blocked.status == "veto"
    assert blocked.reason_key == "gate.positions.total_lots"
    clear = evaluate_max_total_lots(RiskSnapshot(open_lots=0.2, proposed_lot=0.4))
    assert clear.status == "pass"


def test_breakeven_after_tp1_and_news_shield() -> None:
    position = ManagedPosition(
        ticket="t1",
        direction="buy",
        entry=2650,
        stop=2640,
        lot=1.0,
        targets=[2660, 2670],
    )
    actions = plan_position_actions(
        position,
        live_px=2661,
        atr=2,
        minutes_to_news=5,
        can_modify=True,
    )
    kinds = {item.kind for item in actions}
    assert "breakeven" in kinds
    assert "secure" in kinds
    assert all(item.apply for item in actions if item.kind in {"breakeven", "secure"})


def test_partial_and_momentum_exit_respect_grants() -> None:
    position = ManagedPosition("t2", "buy", 2650, 2640, 1.0, [2660])
    candles = [_candle(2662, volume=10, up=False), _candle(2661, volume=1, up=False)]
    actions = plan_position_actions(
        position,
        live_px=2662,
        atr=2,
        candles=candles,
        can_partial=False,
        can_close=False,
    )
    by_kind = {item.kind: item for item in actions}
    assert by_kind["partial"].apply is False
    assert by_kind["exit"].apply is False

    held = plan_position_actions(
        position,
        live_px=2662,
        atr=2,
        minutes_to_news=5,
        candles=candles,
        news_shield=False,
        early_exit=False,
    )
    assert "exit" not in {item.kind for item in held}
    assert "secure" not in {item.kind for item in held}


def test_scenario_watch_keeps_the_first_trigger() -> None:
    watch = ScenarioWatch(
        ScenarioSpec("primary", "buy", 2660, 2640),
        ScenarioSpec("alternate", "sell", 2640, 2670),
    )
    assert watch.on_price(2650) is None
    winner = watch.on_price(2660)
    assert winner is not None and winner.id == "primary"
    assert watch.cancelled_id == "alternate"
    assert watch.on_price(2630) is winner


def test_scorecard_win_rate_and_drawdown() -> None:
    card = build_scorecard(
        [{"pnl": 10, "r": 2}, {"pnl": -4, "r": -1}, {"pnl": 6, "r": 1}],
        period="week",
    )
    assert card["trades"] == 3
    assert card["win_rate"] == pytest.approx(2 / 3)
    assert card["pnl"] == 12
    assert card["max_dd"] == 4


def test_warehouse_roundtrip_and_gaps(tmp_path) -> None:
    store = CandleWarehouse(tmp_path / "bars.sqlite")
    bars = [
        Candle(time_ms=0, open=1, high=2, low=0.5, close=1.5, volume=3),
        Candle(time_ms=120_000, open=1.5, high=2, low=1, close=1.8, volume=4),
    ]
    assert store.upsert("XAUUSD", "1m", bars) == 2
    loaded = store.load("XAUUSD", "1m")
    assert [bar.close for bar in loaded] == [1.5, 1.8]
    assert store.gap_count("XAUUSD", "1m", 60_000) == 1
    assert store.last_sync_ms("XAUUSD", "1m") == 120_000
    store.close()


def test_fast_replay_on_a_breakout_series() -> None:
    candles: list[Candle] = []
    price = 100.0
    for index in range(80):
        price += 0.4 if index % 7 else -0.1
        candles.append(
            Candle(
                time_ms=index * 60_000,
                open=price - 0.2,
                high=price + 0.8,
                low=price - 0.8,
                close=price,
                volume=10,
            )
        )
    result = replay(candles)
    assert result["ok"] is True
    assert result["strategy"] == "atr_breakout"
    assert result["candles"] == 80


def test_range_silence_blocks_proactive_broadcast() -> None:
    assert silence_blocks(regime="range", material_change=False) is True
    assert broadcast_channels(["telegram", "telegram"], regime="range", material_change=False) == []
    assert broadcast_channels(["telegram", "websocket"], regime="trend") == [
        "telegram",
        "websocket",
    ]


def test_feed_health_marks_a_stale_stream() -> None:
    note_tick(1_000)
    assert feed_health(1_000)["state"] == "live"
    stale = feed_health(1_000 + 10 * 60 * 1000)
    assert stale["state"] == "feed_disconnected"


def test_daily_wrap_and_postmortem_are_structured(tmp_path) -> None:
    journal = tmp_path / "memory" / "journal.jsonl"
    saved = record_daily_wrap_answer(journal, day="2026-09-26", answer="Waited for London.")
    assert saved["answer"] == "Waited for London."
    assert journal.is_file()
    note = postmortem_artifact(plan_id="p1", direction="buy", entry=2650, stop=2640)
    assert note["outcome"] == "invalidated"
    assert note["prompt_key"] == "behaviour.postmortem"


class _PendingTransport(NullTransport):
    def __init__(self) -> None:
        super().__init__()
        self.market: list[dict] = []
        self.pending: list[dict] = []

    async def account_snapshot(self) -> dict:
        return {"ok": True, "account": {"balance": 10_000, "equity": 10_000, "marginLevel": 900}}

    async def quote(self, symbol: str) -> dict:
        return {"ok": True, "quote": {"bid": 2650.0, "ask": 2650.2}}

    async def open_positions(self) -> list[dict]:
        return []

    async def send_market(self, payload: dict) -> dict:
        self.market.append(payload)
        return {"ok": True, "result": {"positionId": "m1"}}

    async def send_pending(self, payload: dict) -> dict:
        self.pending.append(payload)
        return {"ok": True, "result": {"orderId": "o1"}}


@pytest.mark.asyncio
async def test_limit_confirm_sends_pending_not_market(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = _PendingTransport()
    set_transport_for_tests(transport)
    monkeypatch.setattr("nanobot.trading.mt5_execution.time.time", lambda: SAFE_TS)
    monkeypatch.setattr("nanobot.trading.mt5_proposals.time.time", lambda: SAFE_TS)
    try:
        proposed = await mt5_propose_order(
            side="buy",
            entry=2650.0,
            stop=2640.0,
            targets=[2670.0],
            lot=0.1,
            order_type="limit",
        )
        assert proposed["executed"] is False
        out = await mt5_confirm_order(proposal_id=proposed["proposal"]["id"], confirm=True)
        assert out["executed"] is True
        assert transport.market == []
        assert transport.pending[0]["kind"] == "limit"
        assert transport.pending[0]["price"] == 2650.0
    finally:
        set_transport_for_tests(None)


def test_conversation_scenarios_name_real_tools() -> None:
    """Labeled scenarios name tools. Selection stays with the model, not a keyword router."""
    from nanobot.agent.tools.context import ToolContext
    from nanobot.agent.tools.loader import ToolLoader
    from nanobot.agent.tools.registry import ToolRegistry
    from nanobot.config.schema import ToolsConfig

    scenarios = {
        "live_quote": "get_gold_quote",
        "analyze": "analyze_gold",
        "kernel": "run_trading_kernel",
        "team": "run_trading_team",
        "propose": "mt5_propose_order",
        "confirm": "mt5_confirm_order",
        "modify": "mt5_modify_order",
        "close": "mt5_close_position",
        "cancel_pending": "mt5_cancel_order",
        "intel": "gold_intel_scan",
        "evidence": "fetch_evidence",
        "backtest": "fast_backtest",
    }
    assert len(scenarios) >= 10
    registry = ToolRegistry()
    ctx = ToolContext(config=ToolsConfig(), workspace="/tmp", timezone="UTC")
    names = set(ToolLoader().load(ctx, registry))
    missing = set(scenarios.values()) - names
    assert not missing, missing
