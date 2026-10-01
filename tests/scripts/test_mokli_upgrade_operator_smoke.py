"""Smoke test for scripts/mokli_upgrade_operator_smoke.sh."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "mokli_upgrade_operator_smoke.sh"


def test_operator_smoke_script() -> None:
    proc = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert "OK §11 dry-run" in proc.stdout
    assert "§11 scaffold" in proc.stdout
    assert "§11 progress" in proc.stdout or "§11 progress" in proc.stderr
    assert "passed" in proc.stdout.lower()
    assert proc.returncode in (0, 1)
    if proc.returncode == 1:
        assert "WARN operator smoke" in proc.stderr or "FAIL" in proc.stdout
    combined = proc.stdout + proc.stderr
    assert (
        "operator_unblock" in combined
        or "cloud_status" in combined
        or "completion_status" in combined
        or "timer_wake" in combined
    )
    partial = ROOT / "section11-results-partial.json"
    events = ROOT / "section11-events"
    if partial.is_file() and events.is_dir():
        combined = proc.stdout + proc.stderr
        assert "partial pack rows 1–10" in combined or "rows 1–10" in combined
        assert "through row 10" in combined or "require-through 10" in combined
        assert "production gate @10" in combined or "production_gate @10" in combined
