"""Tests for scripts/mokli_upgrade_section11_validate.py"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "mokli_upgrade_section11_validate.py"


def test_validate_ok_when_complete(tmp_path: Path) -> None:
    (tmp_path / "01-greeting.jsonl").write_text(
        json.dumps({"kind": "diagnostic", "data": {"rounds": 1, "input_tokens": 10}}) + "\n",
        encoding="utf-8",
    )
    results = tmp_path / "results.json"
    results.write_text(json.dumps({"1": "PASS"}), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--dir",
            str(tmp_path),
            "--results",
            str(results),
            "--require-through",
            "1",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "OK §11" in proc.stdout


def test_validate_fails_on_empty_result(tmp_path: Path) -> None:
    (tmp_path / "01-greeting.jsonl").write_text(
        json.dumps({"kind": "diagnostic", "data": {"rounds": 1}}) + "\n",
        encoding="utf-8",
    )
    results = tmp_path / "results.json"
    results.write_text(json.dumps({"1": ""}), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--dir",
            str(tmp_path),
            "--results",
            str(results),
            "--require-through",
            "1",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "Empty" in proc.stderr or "Empty" in proc.stdout


def test_validate_rejects_dry_run_when_require_multiple_rows(tmp_path: Path) -> None:
    for row_id in (1, 2):
        (tmp_path / f"{row_id:02d}-scenario.jsonl").write_text(
            json.dumps({"kind": "diagnostic", "data": {"rounds": 1}}) + "\n",
            encoding="utf-8",
        )
    results = tmp_path / "results.json"
    results.write_text(
        json.dumps({1: "DRY-RUN — fixture", 2: "PASS live"}),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--dir",
            str(tmp_path),
            "--results",
            str(results),
            "--require-through",
            "2",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "DRY-RUN" in proc.stderr


def test_validate_prints_progress_on_failure(tmp_path: Path) -> None:
    (tmp_path / "01-greeting.jsonl").write_text(
        json.dumps({"kind": "diagnostic", "data": {"rounds": 1}}) + "\n",
        encoding="utf-8",
    )
    results = tmp_path / "results.json"
    results.write_text(json.dumps({1: "PASS", 2: ""}), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--dir",
            str(tmp_path),
            "--results",
            str(results),
            "--require-through",
            "2",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "§11 progress" in proc.stderr
    assert "  1: ready" in proc.stderr
    assert "  2: incomplete" in proc.stderr


def test_example_results_template_fails_production_gate(tmp_path: Path) -> None:
    """docs/section11-results.example.json must not pass --require-through 13."""
    fixture = ROOT / "tests" / "fixtures" / "section11_turn_diagnostics_sample.jsonl"
    (tmp_path / "01-no-tools.jsonl").write_text(
        fixture.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    example = ROOT / "docs" / "section11-results.example.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--dir",
            str(tmp_path),
            "--results",
            str(example),
            "--require-through",
            "13",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "Missing JSONL" in proc.stderr or "Empty" in proc.stderr
