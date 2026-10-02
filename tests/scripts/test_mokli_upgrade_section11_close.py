"""Tests for scripts/mokli_upgrade_section11_close.sh"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "mokli_upgrade_section11_close.sh"


def test_section11_close_dry_run(tmp_path: Path) -> None:
    events = tmp_path / "events"
    events.mkdir()
    (events / "01-greeting.jsonl").write_text(
        json.dumps({"kind": "diagnostic", "data": {"rounds": 1, "request_input_tokens": 10}})
        + "\n",
        encoding="utf-8",
    )
    results = tmp_path / "section11-results.json"
    results.write_text(json.dumps({"1": "PASS"}), encoding="utf-8")
    report = tmp_path / "report.md"
    report.write_text("| # | a | b | c | d | e | f |\n| 1 | p | q | r | | |\n", encoding="utf-8")

    proc = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--dir",
            str(events),
            "--results",
            str(results),
            "--report",
            str(report),
            "--require-through",
            "1",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "OK §11 artifacts" in proc.stdout
    assert "| PASS |" in proc.stdout
    assert "would update" in proc.stdout
    assert "PASS" not in report.read_text(encoding="utf-8")


def test_section11_close_aborts_when_validate_fails_on_repo_partial() -> None:
    events = ROOT / "section11-events"
    partial = ROOT / "section11-results-partial.json"
    if not events.is_dir() or not partial.is_file():
        return
    proc = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--dir",
            str(events),
            "--results",
            str(partial),
            "--require-through",
            "13",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert proc.returncode != 0, proc.stdout
    combined = proc.stdout + proc.stderr
    assert "validate rows 1..13" in combined
    assert "ERROR" in combined
    assert (
        "Row 5 diagnostic" in combined
        or "Missing JSONL" in combined
        or "Missing 01-no-tools-after-p0" in combined
    )
    assert re.search(r"closure_errors=[1-9]\d*", combined)
    assert "close_summary:" in combined
    assert "seconds_until_reset=" in combined
    if (ROOT / "section11-events").is_dir() and (ROOT / "section11-results-partial.json").is_file():
        assert "live_rerun_rows=" in combined


def test_section11_close_script_promotes_partial_on_apply_at_13() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "section11-results-partial.json" in text
    assert "OK promoted partial results" in text


def test_section11_close_rejects_apply_with_allow_partial(tmp_path: Path) -> None:
    events = tmp_path / "events"
    events.mkdir()
    (events / "01-greeting.jsonl").write_text(
        json.dumps({"kind": "diagnostic", "data": {"rounds": 1, "input_tokens": 1}}) + "\n",
        encoding="utf-8",
    )
    results = tmp_path / "results.json"
    results.write_text(json.dumps({1: "PARTIAL — x"}), encoding="utf-8")
    proc = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--dir",
            str(events),
            "--results",
            str(results),
            "--require-through",
            "13",
            "--allow-partial",
            "--apply",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "allow-partial" in proc.stderr.lower() or "allow-partial" in proc.stdout.lower()


def test_section11_close_dry_run_allows_partial_when_flag_set(tmp_path: Path) -> None:
    events = tmp_path / "events"
    events.mkdir()
    for row_id in (1, 2):
        (events / f"{row_id:02d}-x.jsonl").write_text(
            json.dumps({"kind": "diagnostic", "data": {"rounds": 1, "input_tokens": 1}}) + "\n",
            encoding="utf-8",
        )
    results = tmp_path / "results.json"
    results.write_text(json.dumps({1: "PASS", 2: "PARTIAL — y"}), encoding="utf-8")
    proc = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--dir",
            str(events),
            "--results",
            str(results),
            "--require-through",
            "2",
            "--allow-partial",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "batch markdown" in proc.stdout.lower() or "|" in proc.stdout


def test_section11_close_apply_writes_report(tmp_path: Path) -> None:
    events = tmp_path / "events"
    events.mkdir()
    (events / "01-greeting.jsonl").write_text(
        json.dumps({"kind": "diagnostic", "data": {"rounds": 2, "request_input_tokens": 99}})
        + "\n",
        encoding="utf-8",
    )
    results = tmp_path / "section11-results.json"
    results.write_text(json.dumps({"1": "PASS — applied"}), encoding="utf-8")
    report = tmp_path / "report.md"
    report.write_text(
        "| # | a | b | c | d | e | f |\n| 1 | p | q | r | | |\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--dir",
            str(events),
            "--results",
            str(results),
            "--report",
            str(report),
            "--require-through",
            "1",
            "--apply",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "OK §11 close" in proc.stdout
    assert "report gate" not in proc.stdout.lower()
    body = report.read_text(encoding="utf-8")
    assert "PASS — applied" in body
    assert "rounds=2" in body and "in=99" in body


def test_section11_close_apply_updates_real_report_unicode_header(tmp_path: Path) -> None:
    """Regression: close --apply must flip §11 title on docs/mokli-agent-upgrade-report.md shape."""
    report_src = ROOT / "docs" / "mokli-agent-upgrade-report.md"
    source = report_src.read_text(encoding="utf-8")
    header = "## 11. مسارات حية (لم تُنفَّذ في Cloud Agent)"
    row1 = next(line for line in source.splitlines() if line.startswith("| 1 |"))
    events = tmp_path / "events"
    events.mkdir()
    (events / "01-no-tools.jsonl").write_text(
        json.dumps(
            {
                "kind": "diagnostic",
                "data": {
                    "rounds": 1,
                    "request_input_tokens": 9500,
                    "request_output_tokens": 80,
                    "tool_calls": 0,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    results = tmp_path / "section11-results.json"
    results.write_text(json.dumps({"1": "PASS — no-tools live"}), encoding="utf-8")
    report = tmp_path / "report.md"
    report.write_text(
        f"{header}\n| # | المسار | ماذا تفعل | ماذا تثبت | النتيجة | أرقام |\n{row1}\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--dir",
            str(events),
            "--results",
            str(results),
            "--report",
            str(report),
            "--require-through",
            "1",
            "--apply",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    body = report.read_text(encoding="utf-8")
    assert "PASS — no-tools live" in body
    assert "rounds=1" in body and "in=9500" in body
    assert "تم التعبئة من تشغيل VPS" in body
    assert "Cloud Agent" not in body.split("###", 1)[0]


def test_close_apply_on_canonical_report_aborts_before_patch(tmp_path: Path) -> None:
    """Incomplete §11 artifacts must not mutate docs/mokli-agent-upgrade-report.md."""
    canonical = ROOT / "docs" / "mokli-agent-upgrade-report.md"
    before = canonical.read_text(encoding="utf-8")
    events = tmp_path / "events"
    events.mkdir()
    results = tmp_path / "section11-results.json"
    results.write_text(json.dumps({"1": "PASS — should not land"}), encoding="utf-8")
    proc = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--dir",
            str(events),
            "--results",
            str(results),
            "--report",
            str(canonical),
            "--require-through",
            "13",
            "--apply",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0
    assert canonical.read_text(encoding="utf-8") == before
    assert "report gate" not in proc.stdout.lower()
    assert "OK §11 close" not in proc.stdout


def test_close_uses_validate_shell_wrapper() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "mokli_upgrade_section11_validate.sh" in text
    assert "print-live-rerun-rows" in text
    assert text.count("mokli_upgrade_section11_validate.py") == 1
