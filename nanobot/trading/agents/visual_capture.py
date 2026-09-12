"""Best-effort TradingView visual evidence. Missing frames degrade, never abort."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from nanobot.trading.types import VisualReview

LEAD_FRAMES: dict[str, list[str]] = {
    "1m": ["1m", "5m", "15m"],
    "5m": ["5m", "15m", "1h"],
    "15m": ["15m", "1h", "4h"],
    "30m": ["30m", "1h", "4h"],
    "1h": ["1h", "4h", "1d"],
    "4h": ["4h", "1d"],
    "1d": ["1d"],
}

CaptureFn = Callable[[list[str]], Awaitable[dict[str, Any]]]


def visual_timeframes(lead: str) -> list[str]:
    return list(LEAD_FRAMES.get(lead, ["15m", "1h", "4h"]))


async def capture_visual_evidence(
    lead: str = "15m",
    *,
    capture: CaptureFn | None = None,
) -> tuple[VisualReview, list[dict[str, Any]]]:
    requested = visual_timeframes(lead)
    if capture is None:
        return (
            VisualReview(
                state="not_checked",
                requested=requested,
                captured=[],
                missing=list(requested),
                notes="No chart snapshot was available. Analysis proceeds on numbers alone.",
            ),
            [],
        )
    try:
        raw = await capture(requested)
    except Exception as exc:
        return (
            VisualReview(
                state="not_checked",
                requested=requested,
                captured=[],
                missing=list(requested),
                notes=f"Chart capture failed ({exc}). Numbers-only read.",
            ),
            [],
        )
    frames = raw.get("frames") if isinstance(raw, dict) else None
    snapshots: list[dict[str, Any]] = []
    captured: list[str] = []
    if isinstance(frames, list):
        for frame in frames:
            if not isinstance(frame, dict):
                continue
            tf = str(frame.get("timeframe") or "")
            if tf:
                captured.append(tf)
                snapshots.append(frame)
    missing = [tf for tf in requested if tf not in captured]
    if not captured:
        state = "not_checked"
        notes = "No chart snapshot was available. Analysis proceeds on numbers alone."
    elif missing:
        state = "partial"
        notes = f"Shown: {', '.join(captured)}. Not shown: {', '.join(missing)}."
    else:
        state = "checked"
        notes = f"Read charts for {', '.join(captured)}."
    return (
        VisualReview(
            state=state,
            requested=requested,
            captured=captured,
            missing=missing,
            notes=notes,
        ),
        snapshots,
    )
