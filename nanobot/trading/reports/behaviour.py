"""Post-mortem artifact and end-of-day reflective prompt (T-9.2, T-9.4)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def postmortem_artifact(
    *,
    plan_id: str,
    direction: str,
    entry: float,
    stop: float,
    outcome: str = "invalidated",
) -> dict[str, Any]:
    return {
        "kind": "post_mortem",
        "plan_id": plan_id,
        "direction": direction,
        "entry": entry,
        "stop": stop,
        "outcome": outcome,
        "prompt_key": "behaviour.postmortem",
    }


def daily_wrap_prompt(day: str) -> dict[str, Any]:
    return {"kind": "daily_wrap", "day": day, "prompt_key": "behaviour.daily_wrap", "answer": None}


def append_journal(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def record_daily_wrap_answer(path: Path, *, day: str, answer: str) -> dict[str, Any]:
    record = daily_wrap_prompt(day)
    record["answer"] = answer.strip()
    append_journal(path, record)
    return record
