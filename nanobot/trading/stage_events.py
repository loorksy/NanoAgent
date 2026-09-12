"""Agent stage events — English wire labels + Arabic Telegram labels."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Literal

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
})

STAGE_LABEL_EN: dict[str, str] = {
    "market_data": "Market data",
    "structure": "Price structure",
    "liquidity": "Liquidity",
    "supply_demand": "Supply & demand",
    "multi_timeframe": "Multi-timeframe",
    "news": "News & events",
    "risk": "Risk filters",
    "final_decision": "Final decision",
    "drawing": "Chart drawing",
    "execution_guard": "Execution guard",
    "general": "Answer",
    "research": "Research",
}

STAGE_LABEL_AR: dict[str, str] = {
    "market_data": "جاري جلب بيانات السوق",
    "structure": "تحليل البنية السعرية",
    "liquidity": "تحليل السيولة",
    "supply_demand": "مناطق العرض والطلب",
    "multi_timeframe": "تحليل الأطر الزمنية",
    "news": "فحص الأخبار والأحداث",
    "risk": "تقييم المخاطر والمرشحين",
    "final_decision": "اتخاذ القرار النهائي",
    "drawing": "رسم التحليل على الشارت",
    "execution_guard": "حارس التنفيذ",
    "general": "الإجابة",
    "research": "البحث",
}


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
    if locale.startswith("ar"):
        return STAGE_LABEL_AR.get(stage, stage)
    return STAGE_LABEL_EN.get(stage, stage)
