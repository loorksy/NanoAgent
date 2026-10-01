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


def test_header_update_on_real_report_pending_unicode() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from mokli_upgrade_section11_patch_report import apply_section11_patch

    text = (
        "## 11. مسارات حية (لم تُنفَّذ في Cloud Agent)\n"
        "| # | a | b | c | d | e | f |\n"
        "| 1 | p | q | r | | |\n"
    )
    payloads = {1: ("PASS live", "rounds=1 in=10 out=1 tools=0")}
    updated, changed = apply_section11_patch(text, payloads, require_through=1)
    assert changed >= 2
    assert "تم التعبئة من تشغيل VPS" in updated
    assert "Cloud Agent" not in updated.split("###", 1)[0]


def test_apply_section11_patch_updates_header_when_rows_complete() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from mokli_upgrade_section11_patch_report import apply_section11_patch

    text = (
        "## 11. مسارات حية (لم تُنفَّذ في Cloud Agent)\n"
        "| # | a | b | c | d | e | f |\n"
        "| 1 | p | q | r | | |\n"
        "| 2 | x | y | z | | |\n"
    )
    payloads = {
        1: ("PASS 1", "rounds=1 in=10"),
        2: ("PASS 2", "rounds=2 in=20"),
    }
    updated, changed = apply_section11_patch(text, payloads, require_through=2)
    assert changed == 3
    assert "تم التعبئة من تشغيل VPS" in updated
    assert "لم تُنفَّذ في Cloud Agent" not in updated


def test_patch_preserves_real_report_section11_rows_1_through_14() -> None:
    """Regression: every §11 data row in docs/mokli-agent-upgrade-report.md is patchable."""
    import re

    sys.path.insert(0, str(ROOT / "scripts"))
    from mokli_upgrade_section11_patch_report import patch_report_text

    report_path = ROOT / "docs" / "mokli-agent-upgrade-report.md"
    text = report_path.read_text(encoding="utf-8")
    row_lines: dict[int, str] = {}
    in_live_table = False
    for line in text.splitlines():
        if line.startswith("## 11. مسارات حية"):
            in_live_table = True
            continue
        if in_live_table and line.startswith("### 11.1"):
            break
        if not in_live_table:
            continue
        if line.startswith("| ---") or line.startswith("| # |"):
            continue
        match = re.match(r"^\|\s*(\d+)\s*\|", line)
        if not match:
            continue
        row_id = int(match.group(1))
        row_lines[row_id] = line

    assert row_lines[1].startswith("| 1 |")
    assert "`diagnostic`" in row_lines[1]
    assert min(row_lines) == 1 and max(row_lines) >= 13

    header = "| # | المسار | ماذا تفعل | ماذا تثبت | النتيجة | أرقام |\n"
    for row_id, row_line in sorted(row_lines.items()):
        parts = row_line.rstrip().split("|")
        if len(parts) >= 7 and parts[5].strip() and parts[6].strip():
            continue
        assert row_line.rstrip().endswith("| | |"), row_id
        payloads = {row_id: (f"PASS row {row_id}", f"rounds={row_id} in=100 out=1 tools=0")}
        updated, changed = patch_report_text(header + row_line + "\n", payloads)
        assert changed == 1, row_id
        assert f"PASS row {row_id}" in updated
        assert f"rounds={row_id} in=100" in updated
        path_cell = row_line.split("|", 3)[2].strip()
        assert path_cell in updated
