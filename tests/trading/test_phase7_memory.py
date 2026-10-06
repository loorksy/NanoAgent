"""Phase 7 memory, macro, circuit, and strategy-lab units."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from aiohttp import web

from mokli.agent_api.routes.jobs import register as register_jobs
from mokli.agent_api.routes.log import register as register_log
from mokli.agent_api.routes.settings import capabilities_view, public_models, system_view
from mokli.agent_api.routes.settings import register as register_settings
from mokli.trading.backtest.engine import replay
from mokli.trading.backtest.validation import bootstrap_expectancy, monte_carlo, walk_forward
from mokli.trading.bots.circuit import StrategyCircuit
from mokli.trading.bots.opportunity import imminent_events, scan_opportunities, tradability
from mokli.trading.closed_market import closed_market_plan
from mokli.trading.cron import run_cot_job, run_event_monitor_job
from mokli.trading.intel.calendar_view import parse_event_time, rows_from_events, upcoming_rows
from mokli.trading.intel.cases import CaseIndex
from mokli.trading.intel.cot import cot_bias, load_gold_cot, rows_from_cftc, snapshot_from_rows
from mokli.trading.intel.lessons import lesson_from_loss
from mokli.trading.memory.scenarios import ScenarioMemory
from mokli.trading.strategy_lab import propose_strategy
from mokli.trading.types import Candle


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


def test_case_index_adds_note_column_on_old_tables(tmp_path) -> None:
    import sqlite3

    path = tmp_path / "legacy.sqlite"
    with sqlite3.connect(path) as db:
        db.execute(
            """
            CREATE TABLE cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setup TEXT NOT NULL,
                side TEXT NOT NULL,
                regime TEXT NOT NULL,
                atr_bucket TEXT NOT NULL,
                outcome_r REAL NOT NULL
            )
            """
        )
    index = CaseIndex(path)
    index.record(setup="breakout", side="buy", regime="trend", atr=4.2, outcome_r=1.0)
    ranked = index.similar(setup="breakout", side="buy", regime="trend", atr=4.2)
    assert ranked[0]["note"] == ""
    assert ranked[0]["closes"] == []


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
    validation = proposal["validation"]
    assert isinstance(validation, dict)
    assert set(validation) == {"walk_forward", "monte_carlo", "bootstrap"}


def test_replay_exposes_r_multiples_for_validation() -> None:
    card = replay(_candles(40))
    assert card["ok"] is True
    assert card["rs"] == []
    trending: list[Candle] = []
    price = 100.0
    for index in range(80):
        price += 1.2
        trending.append(
            Candle(time_ms=index, open=price - 0.2, high=price + 0.3, low=price - 0.3, close=price)
        )
    traded = replay(trending)
    assert isinstance(traded["rs"], list)
    assert traded["rs"]
    short = walk_forward(_candles(10))
    assert short["ok"] is False
    assert short["reason_key"] == "backtest.not_enough_bars"
    forward = walk_forward(_candles(90), folds=3)
    assert forward["ok"] is True
    folds = forward["folds"]
    assert isinstance(folds, list)
    assert len(folds) == 3


def test_monte_carlo_and_bootstrap_are_seeded() -> None:
    series = [1.0, -0.5, 2.0, -1.0]
    first = monte_carlo(series, paths=40, seed=1)
    second = monte_carlo(series, paths=40, seed=1)
    assert first == second
    assert first["ok"] is True
    assert float(first["p05"]) <= float(first["p50"]) <= float(first["p95"])
    assert monte_carlo([])["ok"] is False
    stats = bootstrap_expectancy([1.0, -1.0, 1.0], samples=30, seed=2)
    assert stats["ok"] is True
    assert stats["mean"] == round(1.0 / 3.0, 4)
    assert bootstrap_expectancy([])["ok"] is False


def test_cftc_rows_and_injected_loader() -> None:
    rows = rows_from_cftc(
        [
            {
                "report_date_as_yyyy_mm_dd": "2024-06-11",
                "comm_positions_long_all": 10,
                "comm_positions_short_all": 40,
                "m_money_positions_long_all": 80,
                "m_money_positions_short_all": 20,
            },
            {
                "report_date_as_yyyy_mm_dd": "2024-06-04",
                "noncomm_positions_long_all": 1,
                "noncomm_positions_short_all": 1,
                "prod_merc_positions_long": 2,
                "prod_merc_positions_short": 2,
            },
        ]
    )
    assert rows[-1]["commercial_net"] == -30
    assert rows[-1]["spec_net"] == 60
    seen: dict[str, str] = {}

    def _get(url: str) -> list[dict[str, object]]:
        seen["url"] = url
        return [
            {
                "comm_positions_long_all": 1,
                "comm_positions_short_all": 4,
                "noncomm_positions_long_all": 9,
                "noncomm_positions_short_all": 2,
            }
        ]

    snap = load_gold_cot(http_get=_get)
    assert "72hh-3qpy" in seen["url"]
    assert snap["spec_net"] == 7
    assert snap["bias"] == "bullish"

    def _offline(url: str) -> list[dict[str, object]]:
        del url
        raise OSError("offline")

    assert load_gold_cot(http_get=_offline)["available"] is False


def test_similar_market_blends_playbook_and_pattern(tmp_path) -> None:
    index = CaseIndex(tmp_path / "cases.sqlite")
    path = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 5.0, 4.0, 6.0, 8.0]
    index.record(
        setup="breakout",
        side="buy",
        regime="trend",
        atr=4.2,
        outcome_r=1.5,
        note="london sweep bullish engulfing",
        closes=path,
    )
    index.record(
        setup="fade",
        side="sell",
        regime="range",
        atr=9.0,
        outcome_r=-0.4,
        note="unrelated distribution fade",
        closes=[8.0, 7.0, 6.0, 5.0, 4.0, 3.0, 2.0, 1.0, 2.0, 1.0],
    )
    ranked = index.similar_market(
        setup="breakout",
        side="buy",
        regime="trend",
        atr=4.2,
        note="london sweep bullish engulfing",
        closes=path,
    )
    assert ranked[0]["regime"] == "trend"
    assert "blended" in ranked[0]
    assert float(ranked[0]["playbook"]) > 0
    assert float(ranked[0]["pattern"]) > 0


def test_upcoming_rows_parse_iso_times() -> None:
    parsed = parse_event_time("2024-06-12T12:10:00Z")
    assert parsed is not None
    assert parsed.tzinfo is not None
    naive = parse_event_time("2024-06-12T12:10:00")
    assert naive is not None
    assert naive.tzinfo is UTC
    now = datetime(2024, 6, 12, 12, tzinfo=UTC)
    soon = upcoming_rows(
        [{"title": "CPI", "time": "2024-06-12T12:10:00Z"}],
        now=now,
        within_minutes=30,
    )
    assert soon[0]["title"] == "CPI"
    assert soon[0]["notice_key"] == "calendar.soon"


def test_event_monitor_and_cot_jobs(monkeypatch) -> None:
    soon = (datetime.now(tz=UTC) + timedelta(minutes=5)).isoformat()
    monkeypatch.setattr(
        "mokli.trading.news.forex_factory.fetch_upcoming_events",
        lambda: [{"title": "CPI", "time": soon}],
    )
    assert asyncio.run(run_event_monitor_job()) == "Event monitor: calendar.soon"
    monkeypatch.setattr(
        "mokli.trading.intel.cot.load_gold_cot",
        lambda: {"available": True, "notice_key": "cot.bias_bullish"},
    )
    assert asyncio.run(run_cot_job()) == "COT: cot.bias_bullish"
    monkeypatch.setattr(
        "mokli.trading.intel.cot.load_gold_cot",
        lambda: {"available": False, "notice_key": "cot.bias_neutral"},
    )
    assert asyncio.run(run_cot_job()) is None


def test_settings_views_omit_secrets() -> None:
    system = system_view(timezone="UTC", host="127.0.0.1", port=8766, enabled=True, version="0")
    assert "bootstrap_token" not in system
    assert "token" not in system
    caps = capabilities_view(dream=True, audio=False, image=False, web=True)
    items = caps["items"]
    assert isinstance(items, list)
    assert items[0] == {"key": "dream", "enabled": True}


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
        "mokli",
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
    assert "/api/v2/tasks/lab" in paths
    assert "/api/v2/log/journal" in paths
    assert "/api/v2/log/calendar" in paths
    assert "/api/v2/settings/models" in paths
    assert "/api/v2/settings/capabilities" in paths
    assert "/api/v2/settings/system" in paths
    assert "/api/v2/distribution/apk" in paths
