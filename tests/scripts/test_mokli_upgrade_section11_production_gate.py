"""Tests for scripts/mokli_upgrade_section11_production_gate.sh"""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "mokli_upgrade_section11_production_gate.sh"


def test_production_gate_passes_require_through_to_sync() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert '"$REQUIRE"' in text
    assert 'sync_from_vps.sh' in text
    assert ' "$EVENTS" "$RESULTS" 10' not in text


def test_production_gate_supports_skip_quota() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "--skip-quota" in text
    assert "SKIP_QUOTA" in text
    assert "PRODUCTION_GATE_EXIT" in text


def test_production_gate_at_ten_can_pass_skip_quota_on_repo_partial_pack() -> None:
    events = ROOT / "section11-events"
    partial = ROOT / "section11-results-partial.json"
    if not events.is_dir() or not partial.is_file():
        return
    proc = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--skip-quota",
            "--skip-oanda",
            "--skip-pull",
            "--require-through",
            "10",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    assert "PRODUCTION_GATE_EXIT=0" in proc.stdout


def test_production_gate_at_thirteen_fails_on_repo_partial_pack() -> None:
    events = ROOT / "section11-events"
    partial = ROOT / "section11-results-partial.json"
    if not events.is_dir() or not partial.is_file():
        return
    proc = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--skip-quota",
            "--skip-oanda",
            "--skip-pull",
            "--require-through",
            "13",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert proc.returncode == 1
    assert "PRODUCTION_GATE_EXIT=1" in proc.stderr
    assert "BLOCKERS_EXIT=1" in proc.stderr


def test_production_gate_help() -> None:
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--help"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 2
    assert "Usage" in proc.stderr
    assert "--pull-vps" in proc.stderr
    assert "--skip-quota" in proc.stderr
