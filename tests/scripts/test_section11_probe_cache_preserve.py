"""Tests for scripts/section11_probe_cache_preserve.py"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "section11_probe_cache_preserve.py"


def _import_module():
    sys.path.insert(0, str(ROOT / "scripts"))
    import section11_probe_cache_preserve as mod

    return mod


def test_restore_when_new_is_retry_only_and_backup_has_reset(tmp_path: Path) -> None:
    mod = _import_module()
    reset_ms = 1_790_899_200_000
    backup = tmp_path / "old.jsonl"
    backup.write_text(
        json.dumps(
            {
                "kind": "delta",
                "data": {"text": f"Error 429 X-RateLimit-Reset': '{reset_ms}'"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    new = tmp_path / "new.jsonl"
    new.write_text(
        json.dumps({"kind": "retry", "data": {"error_kind": "rate_limit"}}) + "\n",
        encoding="utf-8",
    )
    assert mod.should_restore_probe_backup(new, backup) is True


def test_no_restore_when_new_has_reset_delta(tmp_path: Path) -> None:
    mod = _import_module()
    reset_ms = 1_790_899_200_000
    backup = tmp_path / "old.jsonl"
    backup.write_text('{"kind": "diagnostic", "data": {}}\n', encoding="utf-8")
    new = tmp_path / "new.jsonl"
    new.write_text(
        json.dumps(
            {
                "kind": "delta",
                "data": {"text": f"free-models-per-day X-RateLimit-Reset': '{reset_ms}'"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    assert mod.should_restore_probe_backup(new, backup) is False


def test_cli_prints_yes_no(tmp_path: Path) -> None:
    reset_ms = 1_790_899_200_000
    backup = tmp_path / "bak.jsonl"
    backup.write_text(
        json.dumps({"kind": "delta", "data": {"text": f"X-RateLimit-Reset': '{reset_ms}'"}})
        + "\n",
        encoding="utf-8",
    )
    new = tmp_path / "new.jsonl"
    new.write_text('{"kind":"retry","data":{"error_kind":"rate_limit"}}\n', encoding="utf-8")
    py = ROOT / ".venv" / "bin" / "python"
    import os

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "scripts")
    proc = subprocess.run(
        [str(py if py.is_file() else "python3"), str(SCRIPT), str(new), str(backup)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == "yes"
