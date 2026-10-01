"""Operator §11 dry-run script (fixture only, no live provider)."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "mokli_upgrade_section11_dry_run.sh"


def test_section11_dry_run_script() -> None:
    proc = subprocess.run(
        ["bash", str(SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    out = proc.stdout
    assert "rounds=1" in out
    assert "OK §11 artifacts" in out
    assert "DRY-RUN" in out
    assert "OK §11 dry-run" in out
