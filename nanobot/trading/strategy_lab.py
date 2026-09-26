"""Strategy proposals from a replay (R14). A proposal is not an order."""

from __future__ import annotations

from typing import cast

from nanobot.trading.backtest.engine import replay
from nanobot.trading.types import Candle


def propose_strategy(name: str, candles: list[Candle]) -> dict[str, object]:
    card = cast(dict[str, object], replay(candles))
    return {
        "name": name,
        "status": "proposed",
        "promoted": False,
        "executed": False,
        "notice_key": "strategy.proposed",
        "backtest": card,
    }
