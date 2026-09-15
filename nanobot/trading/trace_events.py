"""Unified trading trace events for live agent UI."""

from __future__ import annotations

import time
import uuid
from typing import Any, Literal

TraceEventType = Literal[
    "agent_started",
    "trading_stage",
    "tool_call",
    "tool_result",
    "gate_check",
    "decision",
    "approval_required",
    "completed",
    "error",
]


def emit_trace_event(
    event_type: TraceEventType,
    *,
    run_id: str | None = None,
    summary: str = "",
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "type": event_type,
        "run_id": run_id or str(uuid.uuid4()),
        "summary": summary,
        "detail": detail or {},
        "ts": int(time.time() * 1000),
    }
