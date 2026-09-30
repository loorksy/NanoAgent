"""Smoke test for scripts/mokli_upgrade_preflight.sh (syntax + importable paths)."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "mokli_upgrade_preflight.sh"


def test_preflight_script_runs() -> None:
    assert SCRIPT.is_file()
    proc = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    # Agent API may be down in CI; script must exit 0 or 1 with readable output.
    assert proc.returncode in (0, 1)
    assert "Agent API" in proc.stdout or "FAIL" in proc.stdout
    assert "mokli_upgrade_diagnostic_extract" in proc.stdout
    assert "section11_batch" in proc.stdout
    assert "section11_validate" in proc.stdout
