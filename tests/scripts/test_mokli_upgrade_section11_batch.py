"""Tests for scripts/mokli_upgrade_section11_batch.py"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "mokli_upgrade_section11_batch.py"


def test_batch_extracts_sorted_jsonl(tmp_path: Path) -> None:
    (tmp_path / "02-tools.jsonl").write_text(
        json.dumps({"kind": "diagnostic", "data": {"rounds": 2, "input_tokens": 900}}) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "01-greeting.jsonl").write_text(
        json.dumps(
            {
                "kind": "diagnostic",
                "data": {
                    "rounds": 1,
                    "request_input_tokens": 100,
                    "request_output_tokens": 10,
                    "tool_calls": 0,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--dir", str(tmp_path), "--markdown"],
        capture_output=True,
        text=True,
        check=True,
    )
    out = proc.stdout
    assert "| 1 |" in out and "01-greeting" in out
    assert "| 2 |" in out and "02-tools" in out
    assert "rounds=1" in out
    assert "rounds=2" in out
    assert proc.returncode == 0


def test_batch_with_results_json(tmp_path: Path) -> None:
    (tmp_path / "01-greeting.jsonl").write_text(
        json.dumps(
            {"kind": "diagnostic", "data": {"rounds": 1, "request_input_tokens": 50}}
        )
        + "\n",
        encoding="utf-8",
    )
    results = tmp_path / "results.json"
    results.write_text(json.dumps({"1": "OK — greeting"}), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--dir",
            str(tmp_path),
            "--results",
            str(results),
            "--markdown",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "OK — greeting" in proc.stdout
    assert "rounds=1" in proc.stdout
    assert "| النتيجة |" in proc.stdout


def test_batch_markdown_includes_p0_fold_suffix(tmp_path: Path) -> None:
    (tmp_path / "09-long.jsonl").write_text(
        json.dumps(
            {
                "kind": "diagnostic",
                "data": {
                    "rounds": 8,
                    "request_input_tokens": 4000,
                    "referenced_chars_saved": 5000,
                    "folded_candle_chars": 3000,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--dir", str(tmp_path), "--markdown"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "ref_saved=5000" in proc.stdout
    assert "fold_chars=3000" in proc.stdout


def test_batch_missing_diagnostic_exits_nonzero(tmp_path: Path) -> None:
    (tmp_path / "01-empty.jsonl").write_text('{"kind":"delta"}\n', encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--dir", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "no diagnostic" in proc.stdout.lower() or "(no diagnostic)" in proc.stdout
