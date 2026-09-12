"""Stage checkpoint — resume fleet on unchanged candle hash."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from nanobot.trading.types import AgentMarketContext


@dataclass
class StageCheckpoint:
    candle_hash: str
    completed_stages: list[str]
    payloads: dict[str, Any]


def candle_hash(market: AgentMarketContext) -> str:
    tail = market.candles[-3:] if len(market.candles) >= 3 else market.candles
    blob = json.dumps([(c.time_ms, c.close) for c in tail], sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def should_resume(checkpoint: StageCheckpoint | None, market: AgentMarketContext) -> bool:
    if checkpoint is None:
        return False
    return checkpoint.candle_hash == candle_hash(market)
