"""Tests for scripts/mokli_upgrade_section11_patch_report.py"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / "scripts" / "mokli_upgrade_section11_patch_report.py"


def test_patch_table_line_updates_result_and_numbers() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from mokli_upgrade_section11_patch_report import patch_report_text

    sample = (
        "| # | a | b | c | d | e | f |\n"
        "| 1 | path | act | prove | | |\n"
        "| 2 | x | y | z | | |\n"
    )
    payloads = {1: ("PASS live", "rounds=1 in=100 out=10 tools=0")}
    updated, changed = patch_report_text(sample, payloads)
    assert changed == 1
    assert "| PASS live |" in updated
    assert "rounds=1 in=100" in updated
    assert "| 2 | x | y | z | | |" in updated


def test_patch_script_dry_run_after_validate(tmp_path: Path) -> None:
    events = tmp_path / "events"
    events.mkdir()
    (events / "01-greeting.jsonl").write_text(
        json.dumps({"kind": "diagnostic", "data": {"rounds": 1, "request_input_tokens": 50}})
        + "\n",
        encoding="utf-8",
    )
    results = tmp_path / "section11-results.json"
    results.write_text(json.dumps({"1": "PASS — greeting"}), encoding="utf-8")
    report = tmp_path / "report.md"
    report.write_text(
        "| # | a | b | c | d | e | f |\n| 1 | p | q | r | | |\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(PATCH),
            "--dir",
            str(events),
            "--results",
            str(results),
            "--report",
            str(report),
            "--dry-run",
            "--require-through",
            "1",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    assert "would update 1 row" in proc.stdout
    assert "PASS — greeting" not in report.read_text(encoding="utf-8")


def test_patch_script_writes_report_matching_section11_shape(tmp_path: Path) -> None:
    events = tmp_path / "events"
    events.mkdir()
    (events / "01-no-tools.jsonl").write_text(
        json.dumps(
            {
                "kind": "diagnostic",
                "data": {"rounds": 1, "request_input_tokens": 120, "request_output_tokens": 8},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    results = tmp_path / "section11-results.json"
    results.write_text(json.dumps({"1": "PASS — no tools"}), encoding="utf-8")
    report = tmp_path / "report.md"
    report.write_text(
        "| # | المسار | ماذا تفعل | ماذا تثبت | النتيجة | أرقام (توكن/جولات/أدوات/مراحل) |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| 1 | سؤال بلا أدوات | تحية | `diagnostic` بجولة واحدة | | |\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(PATCH),
            "--dir",
            str(events),
            "--results",
            str(results),
            "--report",
            str(report),
            "--require-through",
            "1",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    body = report.read_text(encoding="utf-8")
    assert "PASS — no tools" in body
    assert "rounds=1" in body and "in=120" in body
    assert "| 1 | سؤال بلا أدوات |" in body


def test_patch_preserves_real_report_row_1_arabic_columns() -> None:
    """Regression: §11 row 1 in docs/mokli-agent-upgrade-report.md must be patchable."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from mokli_upgrade_section11_patch_report import patch_report_text

    report_path = ROOT / "docs" / "mokli-agent-upgrade-report.md"
    text = report_path.read_text(encoding="utf-8")
    row1_lines = [ln for ln in text.splitlines() if ln.startswith("| 1 |")]
    assert len(row1_lines) == 1
    row1 = row1_lines[0]
    assert "`diagnostic`" in row1
    assert row1.rstrip().endswith("| | |")

    snippet = (
        "| # | المسار | ماذا تفعل | ماذا تثبت | النتيجة | أرقام |\n"
        f"{row1}\n"
    )
    payloads = {1: ("PASS VPS", "rounds=1 in=500 out=20 tools=0")}
    updated, changed = patch_report_text(snippet, payloads)
    assert changed == 1
    assert "PASS VPS" in updated
    assert "rounds=1 in=500" in updated
    assert "`diagnostic`" in updated
    assert "«ما اسمك؟»" in updated
