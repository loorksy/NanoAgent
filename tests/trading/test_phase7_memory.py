"""Phase 7 memory, macro, circuit, and strategy-lab units."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from aiohttp import web

from nanobot.agent_api.routes.jobs import register as register_jobs
from nanobot.agent_api.routes.log import register as register_log
from nanobot.agent_api.routes.settings import public_models
from nanobot.agent_api.routes.settings import register as register_settings
from nanobot.trading.bots.circuit import StrategyCircuit
from nanobot.trading.bots.opportunity import imminent_events, scan_opportunities, tradability
from nanobot.trading.closed_market import closed_market_plan
from nanobot.trading.intel.calendar_view import rows_from_events
from nanobot.trading.intel.cases import CaseIndex
from nanobot.trading.intel.cot import cot_bias, snapshot_from_rows
from nanobot.trading.intel.lessons import lesson_from_loss
from nanobot.trading.memory.scenarios import ScenarioMemory
from nanobot.trading.strategy_lab import propose_strategy
from nanobot.trading.types import Candle


def _candles(count: int = 40) -> list[Candle]:
    rows: list[Candle] = []
    for index in range(count):
        price = 2300.0 + index * 0.4
        rows.append(
            Candle(
                time_ms=index,
                open=price,
                high=price + 1.5,
                low=price - 0.4,
                close=price + 0.8,
            )
        )
    return rows


def test_weekend_plan_blocks_entries() -> None:
    saturday = datetime(2024, 6, 15, 12, tzinfo=UTC)
    wednesday = datetime(2024, 6, 12, 12, tzinfo=UTC)
    closed = closed_market_plan(now=saturday, last_close=2320, friday_close=2310, atr=8)
    opened = closed_market_plan(now=wednesday, last_close=2320, friday_close=2310, atr=8)
    assert closed["closed"] is True
    assert closed["entries_allowed"] is False
    assert closed["notice_key"] == "closed_market.weekend"
    assert opened["entries_allowed"] is True
    assert opened["notice_key"] == ""


def test_similar_cases_rank_exact_fingerprint(tmp_path) -> None:
    index = CaseIndex(tmp_path / "cases.sqlite")
    index.record(setup="breakout", side="buy", regime="trend", atr=4.2, outcome_r=1.5)
    index.record(setup="breakout", side="buy", regime="range", atr=4.2, outcome_r=-1.0)
    index.record(setup="fade", side="sell", regime="trend", atr=9.0, outcome_r=0.2)
    ranked = index.similar(setup="breakout", side="buy", regime="trend", atr=4.2)
    assert ranked[0]["regime"] == "trend"
    assert float(ranked[0]["score"]) > float(ranked[1]["score"])


def test_cot_bias_and_snapshot() -> None:
    assert cot_bias(10) == "bullish"
    assert cot_bias(-3) == "bearish"
    snap = snapshot_from_rows([{"commercial_net": -5, "spec_net": 12}])
    assert snap["bias"] == "bullish"
    assert snap["available"] is True
    assert snapshot_from_rows([])["available"] is False


def test_lesson_does_not_block() -> None:
    lesson = lesson_from_loss(setup="breakout", reason="news", side="buy")
    assert lesson["blocks"] is False
    assert lesson["kind"] == "lessons"


def test_scenario_memory_stats(tmp_path) -> None:
    memory = ScenarioMemory(tmp_path / "scenarios.sqlite")
    memory.record(regime="trend", scenario_id="a", r_multiple=2.0)
    memory.record(regime="trend", scenario_id="b", r_multiple=-1.0)
    stats = memory.stats("trend")
    assert stats["count"] == 2
    assert stats["wins"] == 1
    assert stats["avg_r"] == 0.5


def test_circuit_trips_after_three_losses() -> None:
    circuit = StrategyCircuit()
    assert circuit.allows("atr") is True
    circuit.note_result("atr", won=False)
    circuit.note_result("atr", won=False)
    tripped = circuit.note_result("atr", won=False)
    assert tripped["safe_mode"] is True
    assert circuit.allows("atr") is False
    circuit.note_result("atr", won=True)
    assert circuit.allows("atr") is True


def test_strategy_proposal_is_not_an_order() -> None:
    proposal = propose_strategy("atr_breakout", _candles())
    assert proposal["executed"] is False
    assert proposal["promoted"] is False
    assert proposal["status"] == "proposed"


def test_opportunity_and_calendar_helpers() -> None:
    assert scan_opportunities(price=None, atr=1, compressed=False) == []
    assert "atr_breakout" in scan_opportunities(price=2300, atr=2, compressed=False)
    assert tradability(spread_points=80, max_spread=60, news_risk="low")["tradable"] is False
    now = datetime(2024, 6, 12, 12, tzinfo=UTC)
    soon = imminent_events(
        [{"title": "CPI", "at": now + timedelta(minutes=10)}],
        now=now,
        within_minutes=30,
    )
    assert soon[0]["notice_key"] == "calendar.soon"
    assert rows_from_events([{"title": "CPI", "impact": "high", "time": "12:30"}])[0]["title"] == "CPI"


def test_models_document_omits_secrets() -> None:
    document = public_models(
        {"openai": {"api_key": "sk-secret", "api_base": "https://api.example"}},
        "nanoagent",
    )
    blob = str(document)
    assert "sk-secret" not in blob
    providers = document["providers"]
    assert isinstance(providers, list)
    assert providers[0]["configured"] is True


def test_phase7_routes_registered() -> None:
    app = web.Application()
    register_jobs(app.router, "/api/v2")
    register_log(app.router, "/api/v2")
    register_settings(app.router, "/api/v2")
    paths = {route.resource.canonical for route in app.router.routes() if route.resource}
    assert "/api/v2/tasks/desk" in paths
    assert "/api/v2/log/journal" in paths
    assert "/api/v2/log/calendar" in paths
    assert "/api/v2/settings/models" in paths
    assert "/api/v2/distribution/apk" in paths
