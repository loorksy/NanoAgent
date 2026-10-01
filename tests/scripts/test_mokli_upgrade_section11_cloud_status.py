"""Smoke test for mokli_upgrade_section11_cloud_status.sh (no full §11 closure)."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "mokli_upgrade_section11_cloud_status.sh"


def test_cloud_status_reports_blockers_and_exits_nonzero_until_row_13() -> None:
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--require-through", "13"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    combined = proc.stdout + proc.stderr
    assert "cloud_status:" in combined
    assert "quota_ok=" in combined
    assert "blockers_ok=" in combined
    assert "HINT: local artifacts rows 1–10 OK" in combined
    assert proc.returncode == 1
