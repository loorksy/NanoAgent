"""Tests for scripts/mokli_upgrade_section11_status.sh"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "mokli_upgrade_section11_status.sh"


def test_status_fails_when_rows_missing(tmp_path: Path) -> None:
    events = tmp_path / "events"
    events.mkdir()
    (events / "01-no-tools.jsonl").write_text(
        json.dumps({"kind": "diagnostic", "data": {"rounds": 1, "request_input_tokens": 10}})
        + "\n",
        encoding="utf-8",
    )
    results = tmp_path / "results.json"
    results.write_text(json.dumps({"1": "PASS"}), encoding="utf-8")
    proc = subprocess.run(
        ["bash", str(SCRIPT), str(events), str(results), "2"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        env={"PATH": "/usr/bin:/bin"},
    )
    assert proc.returncode == 1
    assert "INCOMPLETE" in proc.stderr or "INCOMPLETE" in proc.stdout


def test_status_skip_quota_passes_validate_only(tmp_path: Path) -> None:
    events = tmp_path / "events"
    events.mkdir()
    for idx, name in [(1, "01-no-tools.jsonl"), (2, "02-single-tool.jsonl")]:
        (events / name).write_text(
            json.dumps(
                {"kind": "diagnostic", "data": {"rounds": 1, "request_input_tokens": 100}}
            )
            + "\n",
            encoding="utf-8",
        )
    results = tmp_path / "results.json"
    results.write_text(
        json.dumps({"1": "PASS — one", "2": "PASS — two"}),
        encoding="utf-8",
    )
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--skip-quota", str(events), str(results), "2"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        env={"PATH": "/usr/bin:/bin"},
    )
    assert proc.returncode == 0, proc.stderr
    assert "skip-quota" in proc.stdout


def test_status_reports_closure_errors_on_repo_partial_at_13() -> None:
    events = ROOT / "section11-events"
    partial = ROOT / "section11-results-partial.json"
    if not events.is_dir() or not partial.is_file():
        return
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--skip-quota", "--require-through", "13"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
        env={"PATH": "/usr/bin:/bin"},
    )
    combined = proc.stdout + proc.stderr
    assert proc.returncode == 1
    assert re.search(r"closure_errors=[1-9]\d*", combined)
    assert "seconds_until_reset=" in combined
    assert "INCOMPLETE" in combined


def test_status_require_through_flag(tmp_path: Path) -> None:
    events = tmp_path / "events"
    events.mkdir()
    (events / "01-no-tools.jsonl").write_text(
        json.dumps(
            {"kind": "diagnostic", "data": {"rounds": 1, "request_input_tokens": 100}}
        )
        + "\n",
        encoding="utf-8",
    )
    results = tmp_path / "results.json"
    results.write_text(json.dumps({"1": "PASS — one"}), encoding="utf-8")
    proc = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--skip-quota",
            "--dir",
            str(events),
            "--results",
            str(results),
            "--require-through",
            "1",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        env={"PATH": "/usr/bin:/bin"},
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "require-through=1" in proc.stdout
