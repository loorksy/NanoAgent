"""Tests for scripts/mokli_upgrade_section11_init.sh"""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "mokli_upgrade_section11_init.sh"


def test_init_creates_scaffold_and_prints_progress(tmp_path: Path) -> None:
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--dir", "events", "--results", "results.json", "--require-through", "2"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert (tmp_path / "events").is_dir()
    assert (tmp_path / "results.json").is_file()
    assert "§11 progress" in proc.stderr or "§11 progress" in proc.stdout
    assert "scaffold" in proc.stdout.lower()
