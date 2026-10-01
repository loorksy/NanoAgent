"""Tests for scripts/section11_quota_reset_hint.py"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "section11_quota_reset_hint.py"
PYTHON = ROOT / ".venv" / "bin" / "python"


def test_parses_reset_from_rate_limit_delta(tmp_path: Path) -> None:
    reset_ms = 1_790_899_200_000
    line = json.dumps(
        {
            "kind": "delta",
            "data": {
                "text": (
                    "Error: {'code': 429, 'metadata': {'headers': "
                    f"{{'X-RateLimit-Reset': '{reset_ms}'}}}}"
                ),
            },
        }
    )
    probe = tmp_path / "quota-probe.jsonl"
    probe.write_text(line + "\n", encoding="utf-8")
    py = str(PYTHON if PYTHON.is_file() else "python3")
    proc = subprocess.run(
        [py, str(SCRIPT), str(probe)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "X-RateLimit-Reset" in proc.stderr or "OpenRouter" in proc.stderr
    assert "2026-" in proc.stderr


def test_seconds_flag_prints_remaining(tmp_path: Path) -> None:
    reset_ms = 1_790_899_200_000
    line = json.dumps(
        {
            "kind": "delta",
            "data": {"text": f"X-RateLimit-Reset': '{reset_ms}'"},
        }
    )
    probe = tmp_path / "quota-probe.jsonl"
    probe.write_text(line + "\n", encoding="utf-8")
    py = str(PYTHON if PYTHON.is_file() else "python3")
    proc = subprocess.run(
        [py, str(SCRIPT), "--seconds", str(probe)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert proc.stdout.strip().isdigit() or proc.stdout.strip() == "0"


def test_missing_probe_is_silent(tmp_path: Path) -> None:
    py = str(PYTHON if PYTHON.is_file() else "python3")
    proc = subprocess.run(
        [py, str(SCRIPT), str(tmp_path / "missing.jsonl")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert proc.stderr.strip() == ""
