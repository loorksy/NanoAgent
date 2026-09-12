"""Paper trading ledger."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from nanobot.config.paths import get_data_dir

_LEDGER = get_data_dir() / "trading" / "paper_ledger.jsonl"


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
