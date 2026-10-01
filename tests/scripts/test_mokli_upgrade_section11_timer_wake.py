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


def test_timer_wake_supports_wait_quota_flag() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "--wait-quota" in text
    assert "wait_quota_reset.sh" in text and "--wait" in text
    assert "vps_section11_quota_probe.sh" in text
