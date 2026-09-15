"""News gate policy (G1) — warn vs strict."""

from __future__ import annotations

import os
from typing import Literal

NewsGateMode = Literal["warn", "strict", "off"]


def news_gate_mode() -> NewsGateMode:
    raw = os.environ.get("LONORA_NEWS_GATE_MODE", "warn").strip().lower()
    if raw in {"strict", "off"}:
        return raw  # type: ignore[return-value]
    return "warn"
