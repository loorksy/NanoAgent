"""Agent stage events — wire labels resolved via trading i18n."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Literal

from nanobot.trading.i18n import stage_label as i18n_stage_label

StageStatus = Literal["running", "done", "failed", "resumed"]

KNOWN_STAGES = frozenset({
    "market_data",
    "structure",
    "liquidity",
    "supply_demand",
    "multi_timeframe",
    "news",
    "risk",
    "final_decision",
    "drawing",
    "execution_guard",
    "general",
    "research",
    "macro_drivers",
})


@dataclass(frozen=True)
class StageEvent:
    stage: str
    status: StageStatus
    timestamp: float
    duration_ms: int | None = None

    def to_wire(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "stage": self.stage,
            "status": self.status,
            "timestamp": self.timestamp,
        }
        if self.duration_ms is not None:
            payload["durationMs"] = self.duration_ms
        return payload


def emit_stage(
    stage: str,
    status: StageStatus,
    *,
    duration_ms: int | None = None,
    timestamp: float | None = None,
) -> StageEvent:
    if stage not in KNOWN_STAGES:
        stage = "general"
    return StageEvent(
        stage=stage,
        status=status,
        timestamp=timestamp if timestamp is not None else time.time(),
        duration_ms=duration_ms,
    )


def stage_label(stage: str, locale: str = "en") -> str:
    return i18n_stage_label(stage, locale)
