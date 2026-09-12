"""Append-only decision memory for gold recommendations."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from nanobot.config.paths import get_data_dir
from nanobot.trading.types import AgentMarketContext, FinalDecisionResult

_TRADES_PATH = get_data_dir() / "trading" / "trades.jsonl"


def trades_memory_path() -> Path:
    return _TRADES_PATH


def record_trade_decision(
    recommendation_id: str,
    decision: FinalDecisionResult,
    market: AgentMarketContext,
    *,
    interval: str = "15m",
) -> None:
    """Persist one structured decision for long-term recall and Dream."""
    rec = decision.recommendation
    entry: dict[str, Any] = {
        "id": recommendation_id,
        "ts": int(time.time() * 1000),
        "symbol": rec.symbol or "XAUUSD",
        "interval": interval,
        "direction": decision.decision,
        "confidence": decision.confidence,
        "summary": decision.summary,
        "entry": rec.entry,
        "stop_loss": rec.stop_loss,
        "targets": list(rec.targets or []),
        "execution_state": rec.execution_state,
        "quote_mid": market.quote_mid,
        "key_reasons": list(decision.key_reasons or [])[:5],
        "risk_warnings": list(decision.risk_warnings or [])[:5],
    }
    _TRADES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _TRADES_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def list_recent_decisions(limit: int = 20) -> list[dict[str, Any]]:
    if not _TRADES_PATH.exists():
        return []
    lines = _TRADES_PATH.read_text(encoding="utf-8").splitlines()
    rows: list[dict[str, Any]] = []
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
        if len(rows) >= limit:
            break
    return rows


def format_decisions_for_dream(limit: int = 10) -> str:
    rows = list_recent_decisions(limit)
    if not rows:
        return ""
    lines = ["## Recent gold trade decisions (trades.jsonl)"]
    for row in rows:
        ts = row.get("ts")
        direction = str(row.get("direction", "wait")).upper()
        summary = str(row.get("summary", ""))
        entry = row.get("entry")
        sl = row.get("stop_loss")
        lines.append(
            f"- [{ts}] {direction} @ {entry} SL {sl}: {summary}"
        )
    return "\n".join(lines)
