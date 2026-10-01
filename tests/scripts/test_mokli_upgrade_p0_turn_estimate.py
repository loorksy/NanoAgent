"""Tests for scripts/mokli_upgrade_p0_turn_estimate.py"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "mokli_upgrade_p0_turn_estimate.py"


def test_p0_turn_estimate_short_below_trading(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--workspace",
            str(tmp_path),
            "--compare",
            "مرحبا",
            "حلل الذهب",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    out = proc.stdout
    assert "final=" in out
    assert "tool_defs=" in out
    assert "delta_final=" in out
    delta_line = [line for line in out.splitlines() if line.startswith("delta_final=")][0]
    delta = int(delta_line.split("=", 1)[1].split()[0])
    assert delta > 0
