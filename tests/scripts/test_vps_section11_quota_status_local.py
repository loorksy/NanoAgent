"""Local-dir tests for vps_section11_quota_status.sh (no SSH)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "vps_section11_quota_status.sh"


def test_local_dir_quota_blocked_when_in_zero(tmp_path: Path) -> None:
    events = tmp_path / "events"
    events.mkdir()
    (events / "quota-probe.jsonl").write_text(
        json.dumps(
            {"kind": "diagnostic", "data": {"rounds": 1, "input_tokens": 0, "tool_calls": 0}}
        )
        + "\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--local-dir", str(events)],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(ROOT),
    )
    combined = proc.stdout + proc.stderr
    assert proc.returncode == 1
    assert "QUOTA_BLOCKED" in combined


def test_local_dir_quota_ok_when_in_positive(tmp_path: Path) -> None:
    events = tmp_path / "events"
    events.mkdir()
    (events / "quota-probe.jsonl").write_text(
        json.dumps(
            {"kind": "diagnostic", "data": {"rounds": 1, "input_tokens": 1200, "tool_calls": 0}}
        )
        + "\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--local-dir", str(events)],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(ROOT),
    )
    assert proc.returncode == 0
    assert "QUOTA_OK" in proc.stdout
