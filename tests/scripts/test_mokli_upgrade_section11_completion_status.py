"""Integration smoke for mokli_upgrade_section11_completion_status.sh (no live LLM)."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "mokli_upgrade_section11_completion_status.sh"
EVENTS = ROOT / "section11-events"
PARTIAL = ROOT / "section11-results-partial.json"


def test_completion_status_partial_pack_through_10() -> None:
    if not EVENTS.is_dir() or not PARTIAL.is_file():
        return
    proc = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--require-through",
            "10",
            str(EVENTS),
            str(PARTIAL),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    combined = proc.stdout + proc.stderr
    assert "completion_status:" in combined
    assert "artifact_ok=1" in combined
    assert "SECTION11_COMPLETION_EXIT=0" in combined
    assert proc.returncode == 0


def test_completion_status_require_13_exits_nonzero_without_closure() -> None:
    if not EVENTS.is_dir() or not PARTIAL.is_file():
        return
    proc = subprocess.run(
        ["bash", str(SCRIPT), str(EVENTS), str(PARTIAL)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    combined = proc.stdout + proc.stderr
    assert "require=13" in combined
    assert "SECTION11_COMPLETION_EXIT=1" in combined
    assert "timer_wake.sh --wait-quota" in combined
    assert proc.returncode == 1


def test_completion_status_script_wires_timer_wake_when_blocked() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "timer_wake.sh --wait-quota" in text
    assert "quota_status.sh" in text and "--local-dir" in text
