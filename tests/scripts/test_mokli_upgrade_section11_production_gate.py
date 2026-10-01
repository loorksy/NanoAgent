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
