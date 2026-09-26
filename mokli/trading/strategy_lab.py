"""Strategy proposals from a replay (R14). A proposal is not an order."""

from __future__ import annotations

from typing import cast

from mokli.trading.backtest.engine import replay
from mokli.trading.backtest.validation import bootstrap_expectancy, monte_carlo, walk_forward
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


def propose_strategy(name: str, candles: list[Candle]) -> dict[str, object]:
    card = cast(dict[str, object], replay(candles))
    series = _rs(card)
    return {
        "name": name,
        "status": "proposed",
        "promoted": False,
        "executed": False,
        "notice_key": "strategy.proposed",
        "backtest": card,
        "validation": {
            "walk_forward": walk_forward(candles),
            "monte_carlo": monte_carlo(series),
            "bootstrap": bootstrap_expectancy(series),
        },
    }
