"""Tests for scripts/vps_section11_set_oanda_env.sh (no SSH)."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "vps_section11_set_oanda_env.sh"


def test_set_oanda_requires_credentials() -> None:
    proc = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        env={"PATH": "/usr/bin:/bin"},
    )
    assert proc.returncode == 1
    assert "OANDA_API_TOKEN" in proc.stderr + proc.stdout
