"""Guard the documented aggregate pytest bundle (collect-only; no full run)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "mokli_upgrade_aggregate_pytest.sh"

# Keep in sync with AGENTS.md «Aggregate pytest target» (2462 passed + 1 skipped).
MIN_COLLECTED = 2430


def test_aggregate_pytest_script_exists() -> None:
    assert SCRIPT.is_file()
    assert SCRIPT.stat().st_mode & 0o111


def test_aggregate_pytest_collects_at_least_documented_floor() -> None:
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--collect-only"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    combined = proc.stdout + proc.stderr
    assert proc.returncode == 0, combined
    match = re.search(r"(\d+) tests collected", combined)
    assert match, f"no collection summary in: {combined[-500:]}"
    assert int(match.group(1)) >= MIN_COLLECTED
