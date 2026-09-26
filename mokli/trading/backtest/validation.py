"""Walk-forward, Monte Carlo, and bootstrap checks for a gold replay (R1)."""

from __future__ import annotations

import random
from typing import cast

from mokli.trading.backtest.engine import MIN_BARS, replay
from mokli.trading.types import Candle


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def monte_carlo(rs: list[float], *, paths: int = 200, seed: int = 1) -> dict[str, object]:
    """Shuffle trade R-multiples and report the equity distribution."""
    if not rs:
        return {"ok": False, "paths": 0, "p05": 0.0, "p50": 0.0, "p95": 0.0, "median_max_dd": 0.0}
    rng = random.Random(seed)
    finals: list[float] = []
    drawdowns: list[float] = []
    for _ in range(paths):
        order = list(rs)
        rng.shuffle(order)
        equity = 0.0
        peak = 0.0
        max_dd = 0.0
        for value in order:
            equity += value
            peak = max(peak, equity)
            max_dd = max(max_dd, peak - equity)
        finals.append(equity)
        drawdowns.append(max_dd)
    return {
        "ok": True,
        "paths": paths,
        "p05": round(_percentile(finals, 0.05), 4),
        "p50": round(_percentile(finals, 0.50), 4),
        "p95": round(_percentile(finals, 0.95), 4),
        "median_max_dd": round(_percentile(drawdowns, 0.50), 4),
    }


def bootstrap_expectancy(rs: list[float], *, samples: int = 200, seed: int = 1) -> dict[str, object]:
    """Resample trade R-multiples with replacement and bound the mean."""
    if not rs:
        return {"ok": False, "mean": 0.0, "p05": 0.0, "p95": 0.0, "samples": 0}
    rng = random.Random(seed)
    count = len(rs)
    means: list[float] = []
    for _ in range(samples):
        draw = [rs[rng.randrange(count)] for _ in range(count)]
        means.append(sum(draw) / count)
    return {
        "ok": True,
        "mean": round(sum(rs) / count, 4),
        "p05": round(_percentile(means, 0.05), 4),
        "p95": round(_percentile(means, 0.95), 4),
        "samples": samples,
    }


def walk_forward(candles: list[Candle], *, folds: int = 3) -> dict[str, object]:
    """Replay contiguous folds. Each fold keeps at least ``MIN_BARS`` when possible."""
    if len(candles) < MIN_BARS:
        return {"ok": False, "reason_key": "backtest.not_enough_bars", "folds": []}
    usable = max(1, len(candles) // MIN_BARS)
    fold_count = max(1, min(folds, usable))
    while fold_count > 1 and len(candles) // fold_count < MIN_BARS:
        fold_count -= 1
    size = len(candles) // fold_count
    rows: list[dict[str, object]] = []
    for index in range(fold_count):
        start = index * size
        end = len(candles) if index == fold_count - 1 else (index + 1) * size
        chunk = candles[start:end]
        card = cast(dict[str, object], replay(chunk))
        rows.append(
            {
                "fold": index,
                "candles": len(chunk),
                "ok": bool(card.get("ok")),
                "trades": card.get("trades", 0),
                "expectancy": card.get("expectancy", 0),
            }
        )
    return {"ok": all(bool(row["ok"]) for row in rows), "folds": rows}
