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


def propose_strategy(
    name: str,
    candles: list[Candle],
    *,
    description: str = "",
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
        card = cast(dict[str, object], replay(candles, rules=rules))
    else:
        rules = None
        card = cast(dict[str, object], replay(candles))
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
            "walk_forward": walk_forward(candles, rules=rules),
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
