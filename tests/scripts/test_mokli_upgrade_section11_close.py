"""Tests for scripts/mokli_upgrade_section11_close.sh"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "mokli_upgrade_section11_close.sh"


def test_section11_close_dry_run(tmp_path: Path) -> None:
    events = tmp_path / "events"
    events.mkdir()
    (events / "01-greeting.jsonl").write_text(
        json.dumps({"kind": "diagnostic", "data": {"rounds": 1, "request_input_tokens": 10}})
        + "\n",
        encoding="utf-8",
    )
    results = tmp_path / "section11-results.json"
    results.write_text(json.dumps({"1": "PASS"}), encoding="utf-8")
    report = tmp_path / "report.md"
    report.write_text("| # | a | b | c | d | e | f |\n| 1 | p | q | r | | |\n", encoding="utf-8")

    proc = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--dir",
            str(events),
            "--results",
            str(results),
            "--report",
            str(report),
            "--require-through",
            "1",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "OK §11 artifacts" in proc.stdout
    assert "| PASS |" in proc.stdout
    assert "would update" in proc.stdout
    assert "PASS" not in report.read_text(encoding="utf-8")
