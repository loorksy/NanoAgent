"""End-to-end operator §11 artifact workflow (no live LLM)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BATCH = ROOT / "scripts" / "mokli_upgrade_section11_batch.py"
VALIDATE = ROOT / "scripts" / "mokli_upgrade_section11_validate.py"
PATCH = ROOT / "scripts" / "mokli_upgrade_section11_patch_report.py"


def test_validate_then_batch_markdown(tmp_path: Path) -> None:
    events = tmp_path / "events"
    events.mkdir()
    for row_id, rounds in ((1, 1), (2, 2)):
        (events / f"{row_id:02d}-scenario.jsonl").write_text(
            json.dumps(
                {
                    "kind": "diagnostic",
                    "data": {
                        "rounds": rounds,
                        "request_input_tokens": 100 * row_id,
                        "request_output_tokens": 10,
                        "tool_calls": row_id - 1,
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
    results = tmp_path / "section11-results.json"
    results.write_text(
        json.dumps({1: "PASS row 1", 2: "PASS row 2"}),
        encoding="utf-8",
    )

    validate = subprocess.run(
        [
            sys.executable,
            str(VALIDATE),
            "--dir",
            str(events),
            "--results",
            str(results),
            "--require-through",
            "2",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert validate.returncode == 0, validate.stderr

    batch = subprocess.run(
        [
            sys.executable,
            str(BATCH),
            "--dir",
            str(events),
            "--results",
            str(results),
            "--markdown",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    out = batch.stdout
    assert "PASS row 1" in out and "PASS row 2" in out
    assert "rounds=1" in out and "rounds=2" in out

    report = tmp_path / "report.md"
    report.write_text(
        "| # | a | b | c | d | e | f |\n"
        "| 1 | p | q | r | | |\n"
        "| 2 | x | y | z | | |\n",
        encoding="utf-8",
    )
    patch = subprocess.run(
        [
            sys.executable,
            str(PATCH),
            "--dir",
            str(events),
            "--results",
            str(results),
            "--report",
            str(report),
            "--dry-run",
            "--require-through",
            "2",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert patch.returncode == 0, patch.stderr or patch.stdout
    assert "would update 2 row" in patch.stdout
    assert "PASS row 1" not in report.read_text(encoding="utf-8")
