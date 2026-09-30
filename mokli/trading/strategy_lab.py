"""Strategy proposals from a replay (R14). A proposal is not an order."""

from __future__ import annotations

import json
import uuid
from typing import Any, cast

from mokli.config.paths import get_data_dir
from mokli.trading.backtest.engine import replay
from mokli.trading.backtest.validation import bootstrap_expectancy, monte_carlo, walk_forward
from mokli.trading.strategy_spec import (
    check_logic,
    program_for,
    rules_from_spec,
    spec_from_description,
)
from mokli.trading.types import Candle


def _rs(card: dict[str, object]) -> list[float]:
    raw = card.get("rs")
    if not isinstance(raw, list):
        return []
    values: list[float] = []
    for item in cast(list[object], raw):
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            continue
        values.append(float(item))
    return values


def _strategies_dir():
    path = get_data_dir() / "trading" / "strategies"
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_replay_candles(
    *,
    interval: str = "1h",
    limit: int = 200,
) -> tuple[list[Candle], list[Candle]]:
    """Entry bars and the 4h confirmation bars. Neither download reads a live quote.

    The two windows do not depend on each other, so they start together.
    """
    import contextvars
    from concurrent.futures import ThreadPoolExecutor

    from mokli.trading.market_context import build_agent_market_context

    def _bars(bar_interval: str, bar_limit: int) -> list[Candle]:
        market = build_agent_market_context(
            "XAUUSD",
            bar_interval,
            bar_limit,
            include_quote=False,
        )
        if not market.sync.ok:
            return []
        return list(market.candles)

    confirm_interval = "4h"
    confirm_limit = 80
    if interval == confirm_interval:
        return _bars(interval, limit), []
    with ThreadPoolExecutor(max_workers=2) as pool:
        contexts = [contextvars.copy_context(), contextvars.copy_context()]
        entry_task = pool.submit(contexts[0].run, _bars, interval, limit)
        confirm_task = pool.submit(contexts[1].run, _bars, confirm_interval, confirm_limit)
        return entry_task.result(), confirm_task.result()


def load_market_bars(interval: str = "15m", limit: int = 200) -> list[Candle]:
    """One replay window. The scorecard does not read a live quote."""
    from mokli.trading.market_context import build_agent_market_context

    market = build_agent_market_context("XAUUSD", interval, limit, include_quote=False)
    if not market.sync.ok:
        return []
    return list(market.candles)


def load_warehouse_bars(interval: str = "15m", limit: int = 200) -> list[Candle]:
    """Local store used only after the market feed returns nothing."""
    from pathlib import Path

    from mokli.trading.warehouse import CandleWarehouse

    path = Path.home() / ".mokli" / "warehouse.sqlite"
    if not path.is_file():
        return []
    store = CandleWarehouse(path)
    try:
        return store.load("XAUUSD", interval, limit=limit)
    finally:
        store.close()


def candles_for_replay(
    supplied: list[Candle] | None = None,
    *,
    interval: str = "15m",
    limit: int = 200,
) -> list[Candle]:
    """Caller bars, otherwise the market feed, otherwise the local warehouse."""
    if supplied:
        return list(supplied)
    loaded = load_market_bars(interval, limit)
    if loaded:
        return loaded
    return load_warehouse_bars(interval, limit)


def lab_replay(name: str, supplied: list[Candle] | None = None) -> dict[str, object]:
    """ATR replay for the tasks lab. An empty feed does not invent prices."""
    candles = candles_for_replay(supplied)
    if not candles:
        return {
            "ok": False,
            "reason_key": "trading.market_feed_unconfigured",
            "trades": 0,
            "executed": False,
            "broker_order": False,
        }
    return propose_strategy(name or "atr_breakout", candles)


def model_strategy_brief(proposal: dict[str, object]) -> dict[str, object]:
    """What the model reads. Candle rows, the R series, and the copied test blob stay out."""
    brief: dict[str, object] = {}
    for key in (
        "id",
        "name",
        "status",
        "promoted",
        "executed",
        "broker_order",
        "notice_key",
        "run_state",
        "version",
        "changelog",
        "logic_errors",
        "reason_key",
        "program",
        "saved",
    ):
        if key in proposal:
            brief[key] = proposal[key]
    backtest = proposal.get("backtest")
    if isinstance(backtest, dict):
        brief["backtest"] = {key: value for key, value in backtest.items() if key != "rs"}
    validation = proposal.get("validation")
    if isinstance(validation, dict):
        brief["validation"] = validation
    spec = proposal.get("spec")
    if isinstance(spec, dict):
        brief["spec"] = {
            key: value
            for key, value in spec.items()
            if key not in {"description", "test_results"}
        }
    return brief


def propose_strategy(
    name: str,
    candles: list[Candle],
    *,
    description: str = "",
    confirm_candles: list[Candle] | None = None,
) -> dict[str, object]:
    spec: dict[str, Any] | None = None
    if description.strip():
        spec = spec_from_description(description, name=name)
        errors = check_logic(spec)
        if errors:
            return {
                "name": name,
                "status": "invalid",
                "promoted": False,
                "executed": False,
                "broker_order": False,
                "notice_key": "strategy.invalid",
                "spec": spec,
                "logic_errors": errors,
                "program": None,
            }
        rules = rules_from_spec(spec)
        card = cast(
            dict[str, object],
            replay(candles, rules=rules, confirm_candles=confirm_candles),
        )
    else:
        rules = None
        card = cast(dict[str, object], replay(candles))
    if card.get("ok") is not True:
        refused: dict[str, object] = {
            "name": name,
            "status": "invalid",
            "promoted": False,
            "executed": False,
            "broker_order": False,
            "notice_key": "strategy.invalid",
            "reason_key": card.get("reason_key"),
            "backtest": card,
            "program": None,
        }
        if spec is not None:
            refused["spec"] = spec
        return refused
    series = _rs(card)
    proposal: dict[str, object] = {
        "id": str(uuid.uuid4()),
        "name": name,
        "status": "proposed",
        "promoted": False,
        "executed": False,
        "broker_order": False,
        "notice_key": "strategy.proposed",
        "backtest": card,
        "validation": {
            "walk_forward": walk_forward(
                candles,
                rules=rules,
                confirm_candles=confirm_candles,
            ),
            "monte_carlo": monte_carlo(series),
            "bootstrap": bootstrap_expectancy(series),
        },
    }
    if spec is not None:
        spec = dict(spec)
        spec["run_state"] = "backtested"
        spec["test_results"] = {"backtest": card, "validation": proposal["validation"]}
        proposal["spec"] = spec
        proposal["program"] = program_for(spec)
        proposal["version"] = spec["version"]
        proposal["changelog"] = spec["changelog"]
        proposal["run_state"] = "backtested"
    return proposal


def save_strategy(proposal: dict[str, object]) -> dict[str, object]:
    """Persist a proposal. Saving does not promote it and does not send an order."""
    if proposal.get("status") != "proposed":
        return {"ok": False, "executed": False, "reason": "not_proposed"}
    backtest = proposal.get("backtest")
    if isinstance(backtest, dict) and backtest.get("ok") is not True:
        return {"ok": False, "executed": False, "broker_order": False, "reason": "backtest_failed"}
    strategy_id = str(proposal.get("id") or uuid.uuid4())
    proposal = dict(proposal)
    proposal["id"] = strategy_id
    proposal["run_state"] = "saved"
    proposal["executed"] = False
    path = _strategies_dir() / f"{strategy_id}.json"
    path.write_text(json.dumps(proposal, ensure_ascii=False), encoding="utf-8")
    return {"ok": True, "id": strategy_id, "executed": False, "path": str(path)}


def load_strategy(strategy_id: str) -> dict[str, Any] | None:
    path = _strategies_dir() / f"{strategy_id}.json"
    if not path.exists():
        return None
    loaded = json.loads(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else None


def start_paper(strategy_id: str) -> dict[str, object]:
    """Record a paper action for a saved spec. No broker order is sent."""
    from mokli.trading.paper import record_paper_action

    record = load_strategy(strategy_id)
    if record is None:
        return {"ok": False, "executed": False, "reason": "missing"}
    spec = record.get("spec")
    if isinstance(spec, dict) and spec.get("logic_ok") is False:
        return {"ok": False, "executed": False, "reason": "logic_failed"}
    backtest = record.get("backtest")
    if isinstance(backtest, dict) and backtest.get("ok") is not True:
        return {"ok": False, "executed": False, "broker_order": False, "reason": "backtest_failed"}
    entry = record_paper_action(strategy_id, "paper", note=str(record.get("name") or ""))
    record["run_state"] = "paper"
    record["executed"] = False
    record["broker_order"] = False
    path = _strategies_dir() / f"{strategy_id}.json"
    path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    return {"ok": True, "executed": False, "broker_order": False, "paper": entry, "run_state": "paper"}


def request_live(strategy_id: str, *, approved: bool = False) -> dict[str, object]:
    """Record explicit approval. This lab never places a broker order."""
    record = load_strategy(strategy_id)
    if record is None:
        return {"ok": False, "executed": False, "broker_order": False, "reason": "missing"}
    if not approved:
        return {
            "ok": False,
            "executed": False,
            "broker_order": False,
            "reason": "live_requires_explicit_approval",
        }
    spec = record.get("spec")
    if isinstance(spec, dict) and spec.get("logic_ok") is False:
        return {"ok": False, "executed": False, "broker_order": False, "reason": "logic_failed"}
    backtest = record.get("backtest")
    if isinstance(backtest, dict) and backtest.get("ok") is not True:
        return {"ok": False, "executed": False, "broker_order": False, "reason": "backtest_failed"}
    record["run_state"] = "approval_recorded"
    record["executed"] = False
    record["broker_order"] = False
    changelog = record.get("changelog")
    if isinstance(changelog, list):
        changelog.append("operator approval recorded; broker execution refused")
    path = _strategies_dir() / f"{strategy_id}.json"
    path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    return {
        "ok": True,
        "executed": False,
        "broker_order": False,
        "run_state": "approval_recorded",
        "reason": "approval_recorded_no_broker_order",
    }
