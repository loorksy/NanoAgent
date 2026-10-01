"""Tests for scripts/mokli_upgrade_section11_status.sh"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "mokli_upgrade_section11_status.sh"


def test_status_fails_when_rows_missing(tmp_path: Path) -> None:
    events = tmp_path / "events"
    events.mkdir()
    (events / "01-no-tools.jsonl").write_text(
        json.dumps({"kind": "diagnostic", "data": {"rounds": 1, "request_input_tokens": 10}})
        + "\n",
        encoding="utf-8",
    )
    results = tmp_path / "results.json"
    results.write_text(json.dumps({"1": "PASS"}), encoding="utf-8")
    proc = subprocess.run(
        ["bash", str(SCRIPT), str(events), str(results), "2"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        env={"PATH": "/usr/bin:/bin"},
    )
    assert proc.returncode == 1
    assert "INCOMPLETE" in proc.stderr or "INCOMPLETE" in proc.stdout
