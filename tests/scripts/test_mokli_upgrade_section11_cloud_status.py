"""Smoke test for mokli_upgrade_section11_cloud_status.sh (no full §11 closure)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "mokli_upgrade_section11_cloud_status.sh"


def test_cloud_status_reports_blockers_and_exits_nonzero_until_row_13() -> None:
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--require-through", "13"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    combined = proc.stdout + proc.stderr
    assert "cloud_agent_rev=" in combined
    assert "cloud_status:" in combined
    assert "quota_ok=" in combined
    assert "blockers_ok=" in combined
    assert "partial10_ok=" in combined
    partial = ROOT / "section11-results-partial.json"
    events = ROOT / "section11-events"
    if partial.is_file() and events.is_dir():
        assert "partial10_ok=1" in combined
        assert "partial10_gate=1" in combined
        after_p0 = events / "01-no-tools-after-p0.jsonl"
        assert after_p0.is_file() or "01-no-tools-after-p0.jsonl" in combined
        assert "PARTIAL" in combined
        assert re.search(r"closure_errors=[1-9]\d*", combined)
        assert "allow_partial_closure_errors=2" in combined
        assert "seconds_until_reset=" in combined
        assert "wake_after_buffer_utc=" in combined
        assert "live_rerun_rows=" in combined
    if "git_rev=" in combined:
        assert "agent_api_health=" in combined
    assert proc.returncode == 1


def test_cloud_status_exits_zero_for_artifacts_through_10_when_partial_pack() -> None:
    partial = ROOT / "section11-results-partial.json"
    events = ROOT / "section11-events"
    if not partial.is_file() or not events.is_dir():
        return
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--require-through", "10"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    combined = proc.stdout + proc.stderr
    assert "cloud_status:" in combined
    assert proc.returncode == 0, combined[-800:]
    assert "not production closure" in combined
    assert "partial10_ok=1" in combined
    assert "partial10_gate=1" in combined
    assert "allow_partial_closure_errors=0" in combined
    assert "allow_partial_closure_errors=unknown" not in combined
    assert "allow_partial_closure_errors=0" in combined
    assert "allow_partial_closure_errors=unknown" not in combined
