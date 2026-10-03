"""Dry-run smoke for mokli_upgrade_section11_timer_wake.sh (no live LLM)."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "mokli_upgrade_section11_timer_wake.sh"


def test_timer_wake_dry_run_exits_zero_without_live_probe() -> None:
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--dry-run"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    combined = proc.stdout + proc.stderr
    assert "DRY-RUN" in combined
    assert "TIMER_WAKE_EXIT=0 (dry-run)" in combined
    assert proc.returncode == 0


def test_timer_wake_report_gate_runs_inside_close_not_duplicated() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "mokli_upgrade_section11_close.sh" in text
    assert "test_mokli_upgrade_report_section11_gate" not in text


def test_timer_wake_close_failure_reruns_blockers_and_remaining_rows_hint() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "close @13 failed" in text
    assert "mokli_upgrade_section11_blockers.sh" in text
    assert "remaining_rows.sh" in text


def test_timer_wake_syncs_vps_rev_before_after_reset_wake() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "check_wake.sh" in text and "--sync-vps-rev" in text


def test_timer_wake_supports_wait_quota_flag() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "--wait-quota" in text
    assert "wait_quota_reset.sh" in text and "--wait" in text
    assert "vps_section11_quota_probe.sh" in text
    assert "flock -n 200" in text
    assert "TIMER_WAKE_EXIT=2" in text
    assert "TIMER_WAKE_FINAL_EXIT=" in text


def test_timer_wake_dry_run_wait_quota_mentions_wait_in_preview() -> None:
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--dry-run", "--wait-quota"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    combined = proc.stdout + proc.stderr
    assert "DRY-RUN" in combined and "--wait-quota" in combined
    assert proc.returncode == 0
