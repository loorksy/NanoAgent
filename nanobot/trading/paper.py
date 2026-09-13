"""Paper trading ledger."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from nanobot.config.paths import get_data_dir

_LEDGER = get_data_dir() / "trading" / "paper_ledger.jsonl"


def paper_actions_index() -> dict[str, str]:
    if not _LEDGER.exists():
        return {}
    index: dict[str, str] = {}
    for line in _LEDGER.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        rec_id = str(row.get("recommendation_id") or "")
        action = str(row.get("action") or "")
        if rec_id and action:
            index[rec_id] = action
    return index


def record_paper_action(
    recommendation_id: str,
    action: str,
    *,
    note: str = "",
) -> dict:
    _LEDGER.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "id": str(uuid.uuid4()),
        "recommendation_id": recommendation_id,
        "action": action,
        "note": note,
        "ts": int(time.time() * 1000),
    }
    with _LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry
