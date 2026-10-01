"""Tests for scripts/mokli_upgrade_p0_turn_estimate.py"""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "mokli_upgrade_p0_turn_estimate.py"
PYTHON = ROOT / ".venv" / "bin" / "python"


def test_greeting_shows_provider_tools_and_lower_than_trading_task(tmp_path: Path) -> None:
    py = str(PYTHON if PYTHON.is_file() else "python3")
    proc = subprocess.run(
        [py, str(SCRIPT), "--compare", "مرحبا", "حلل الذهب"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    assert "provider_tools=" in proc.stdout
    lines = [ln for ln in proc.stdout.splitlines() if ln.startswith("msg=")]
    assert len(lines) >= 2
    light = lines[0]
    heavy = lines[1]
    assert "provider_tools=7" in light or "provider_tools=3" in light
    assert int(light.split("provider_tools=")[1].split()[0]) < int(
        heavy.split("provider_tools=")[1].split()[0]
    )
    assert "delta_final=" in proc.stdout
