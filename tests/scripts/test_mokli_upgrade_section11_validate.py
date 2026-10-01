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


def test_validate_hints_row3_when_tool_calls_below_two(tmp_path: Path) -> None:
    for row_id in (1, 2, 3):
        (tmp_path / f"{row_id:02d}-scenario.jsonl").write_text(
            json.dumps(
                {
                    "kind": "diagnostic",
                    "data": {"rounds": 2, "input_tokens": 100, "tool_calls": 1 if row_id == 3 else 0},
                }
            )
            + "\n",
            encoding="utf-8",
        )
    results = tmp_path / "results.json"
    results.write_text(json.dumps({1: "PASS", 2: "PASS", 3: "PARTIAL"}), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--dir",
            str(tmp_path),
            "--results",
            str(results),
            "--require-through",
            "3",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "HINT row 3" in proc.stderr
    assert "vps_section11_row3_multi_tool" in proc.stderr


def test_validate_hints_row5_when_spawn_hit_quota(tmp_path: Path) -> None:
    spawn_line = (
        '{"kind":"tool","data":{"name":"spawn","summary":"429 rate-limit"}}\n'
    )
    diag = json.dumps(
        {
            "kind": "diagnostic",
            "data": {
                "rounds": 4,
                "input_tokens": 100,
                "tool_calls": 4,
                "nested_rounds": 0,
            },
        }
    )
    (tmp_path / "05-subagents.jsonl").write_text(spawn_line + diag + "\n", encoding="utf-8")
    for row_id in (1, 2, 3, 4):
        (tmp_path / f"{row_id:02d}-x.jsonl").write_text(
            json.dumps({"kind": "diagnostic", "data": {"rounds": 1, "tool_calls": 2}}) + "\n",
            encoding="utf-8",
        )
    results = tmp_path / "results.json"
    results.write_text(json.dumps({str(i): "PASS" for i in range(1, 6)}), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--dir",
            str(tmp_path),
            "--results",
            str(results),
            "--require-through",
            "5",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "HINT row 5" in proc.stderr
    assert "vps_section11_row5_subagents" in proc.stderr


def test_validate_hints_row8_when_input_tokens_zero(tmp_path: Path) -> None:
    for row_id in range(1, 9):
        in_tok = 0 if row_id == 8 else 100
        (tmp_path / f"{row_id:02d}-scenario.jsonl").write_text(
            json.dumps(
                {
                    "kind": "diagnostic",
                    "data": {"rounds": 1, "input_tokens": in_tok, "tool_calls": 0},
                }
            )
            + "\n",
            encoding="utf-8",
        )
    results = tmp_path / "results.json"
    results.write_text(json.dumps({str(i): "PASS" for i in range(1, 9)}), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--dir",
            str(tmp_path),
            "--results",
            str(results),
            "--require-through",
            "8",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "HINT row 8" in proc.stderr
    assert "vps_section11_row8_fallback_provider" in proc.stderr


def test_validate_rejects_row3_one_tool_when_require_through_13(tmp_path: Path) -> None:
    (tmp_path / "01-no-tools-after-p0.jsonl").write_text(
        json.dumps({"kind": "diagnostic", "data": {"rounds": 1, "input_tokens": 5000}})
        + "\n",
        encoding="utf-8",
    )
    for row_id in range(1, 14):
        tool_calls = 1 if row_id == 3 else 2
        nested = 0 if row_id == 5 else 1
        in_tok = 100 if row_id != 8 else 100
        (tmp_path / f"{row_id:02d}-scenario.jsonl").write_text(
            json.dumps(
                {
                    "kind": "diagnostic",
                    "data": {
                        "rounds": 1,
                        "input_tokens": in_tok,
                        "tool_calls": tool_calls,
                        "nested_rounds": nested,
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
    results = tmp_path / "results.json"
    results.write_text(
        json.dumps({str(i): "PASS — live" for i in range(1, 14)}),
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
            "13",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "Row 3 diagnostic needs tool_calls≥2" in proc.stderr


def test_validate_rejects_row8_zero_input_when_require_through_13(tmp_path: Path) -> None:
    (tmp_path / "01-no-tools-after-p0.jsonl").write_text(
        json.dumps({"kind": "diagnostic", "data": {"rounds": 1, "input_tokens": 5000}})
        + "\n",
        encoding="utf-8",
    )
    for row_id in range(1, 14):
        in_tok = 0 if row_id == 8 else 100
        (tmp_path / f"{row_id:02d}-scenario.jsonl").write_text(
            json.dumps(
                {
                    "kind": "diagnostic",
                    "data": {"rounds": 1, "input_tokens": in_tok, "tool_calls": 0},
                }
            )
            + "\n",
            encoding="utf-8",
        )
    results = tmp_path / "results.json"
    results.write_text(
        json.dumps({str(i): "PASS — live" for i in range(1, 14)}),
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
            "13",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "Row 8 diagnostic input_tokens=0" in proc.stderr
    assert "vps_section11_row8_fallback_provider" in proc.stderr


def test_validate_hints_row10_when_oanda_missing(tmp_path: Path) -> None:
    body = (
        '{"kind":"tool","data":{"name":"fast_backtest","summary":"market_feed_unconfigured"}}\n'
        + json.dumps({"kind": "diagnostic", "data": {"rounds": 2, "input_tokens": 100, "tool_calls": 1}})
        + "\n"
    )
    (tmp_path / "10-backtest.jsonl").write_text(body, encoding="utf-8")
    for row_id in range(1, 10):
        if row_id == 10:
            continue
        (tmp_path / f"{row_id:02d}-x.jsonl").write_text(
            json.dumps({"kind": "diagnostic", "data": {"rounds": 1, "tool_calls": 2}}) + "\n",
            encoding="utf-8",
        )
    results = tmp_path / "results.json"
    results.write_text(json.dumps({str(i): "PASS" for i in range(1, 11)}), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--dir",
            str(tmp_path),
            "--results",
            str(results),
            "--require-through",
            "10",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "HINT row 10" in proc.stderr
    assert "vps_section11_row10_backtest" in proc.stderr


def test_validate_hints_row1_p0_when_high_in_without_after_p0(tmp_path: Path) -> None:
    (tmp_path / "01-no-tools.jsonl").write_text(
        json.dumps(
            {
                "kind": "diagnostic",
                "data": {"rounds": 1, "request_input_tokens": 10934, "tool_calls": 0},
            }
        )
        + "\n",
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
    assert "HINT row 1 P0" in proc.stderr
    assert "row1_after_p0" in proc.stderr


def test_validate_ignores_empty_duplicate_row_jsonl(tmp_path: Path) -> None:
    (tmp_path / "01-empty.jsonl").write_text('{"kind":"delta"}\n', encoding="utf-8")
    (tmp_path / "01-good.jsonl").write_text(
        json.dumps({"kind": "diagnostic", "data": {"rounds": 1, "input_tokens": 50}})
        + "\n",
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
    assert proc.returncode == 0, proc.stderr


def test_validate_prints_hints_on_failure_when_rows_11_13_empty(tmp_path: Path) -> None:
    for row_id in range(1, 11):
        (tmp_path / f"{row_id:02d}-x.jsonl").write_text(
            json.dumps(
                {
                    "kind": "diagnostic",
                    "data": {"rounds": 1, "input_tokens": 100, "tool_calls": 1 if row_id == 3 else 2},
                }
            )
            + "\n",
            encoding="utf-8",
        )
    results = tmp_path / "results.json"
    payload = {str(i): "PASS" for i in range(1, 11)}
    payload.update({11: "", 12: "", 13: ""})
    results.write_text(json.dumps(payload), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--dir",
            str(tmp_path),
            "--results",
            str(results),
            "--require-through",
            "13",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "HINT row 3" in proc.stderr
    assert "HINT rows [11, 12, 13]" in proc.stderr


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


def test_validate_requires_after_p0_jsonl_when_require_through_13(tmp_path: Path) -> None:
    for row_id in range(1, 14):
        (tmp_path / f"{row_id:02d}-scenario.jsonl").write_text(
            json.dumps({"kind": "diagnostic", "data": {"rounds": 1, "input_tokens": 100}})
            + "\n",
            encoding="utf-8",
        )
    results = tmp_path / "results.json"
    results.write_text(
        json.dumps({row_id: "PASS — live" for row_id in range(1, 14)}),
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
            "13",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "01-no-tools-after-p0.jsonl" in proc.stderr


def test_validate_rejects_partial_results_when_require_through_13(tmp_path: Path) -> None:
    for row_id in range(1, 14):
        (tmp_path / f"{row_id:02d}-scenario.jsonl").write_text(
            json.dumps({"kind": "diagnostic", "data": {"rounds": 1, "input_tokens": 100}})
            + "\n",
            encoding="utf-8",
        )
    results_map = {row_id: "PASS — live" for row_id in range(1, 14)}
    results_map[3] = "PARTIAL — one tool only"
    results = tmp_path / "results.json"
    results.write_text(json.dumps(results_map), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--dir",
            str(tmp_path),
            "--results",
            str(results),
            "--require-through",
            "13",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "PARTIAL" in proc.stderr
    assert "row 3" in proc.stderr.lower() or "[3]" in proc.stderr or "rows [3" in proc.stderr

    proc_ok = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--dir",
            str(tmp_path),
            "--results",
            str(results),
            "--require-through",
            "13",
            "--allow-partial",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc_ok.returncode == 0


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


def test_validate_closure_hints_name_row11_12_13_jsonl(tmp_path: Path) -> None:
    for row_id in range(1, 11):
        (tmp_path / f"{row_id:02d}-x.jsonl").write_text(
            json.dumps({"kind": "diagnostic", "data": {"rounds": 1, "input_tokens": 100}}) + "\n",
            encoding="utf-8",
        )
    results = tmp_path / "results.json"
    payload = {str(i): "PASS" for i in range(1, 11)}
    payload.update({"11": "", "12": "", "13": ""})
    results.write_text(json.dumps(payload), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--dir",
            str(tmp_path),
            "--results",
            str(results),
            "--require-through",
            "13",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "11-paper.jsonl" in proc.stderr
    assert "12-desktop-ui.jsonl" in proc.stderr
    assert "13-mobile.jsonl" in proc.stderr


def test_validate_row9_hint_skips_when_pick_row_has_no_quota_tail(tmp_path: Path) -> None:
    diag = json.dumps(
        {"kind": "diagnostic", "data": {"rounds": 1, "input_tokens": 4000, "tool_calls": 1}}
    )

    def write_rows_through_8() -> None:
        for row_id in range(1, 9):
            (tmp_path / f"{row_id:02d}-x.jsonl").write_text(
                json.dumps({"kind": "diagnostic", "data": {"rounds": 1, "input_tokens": 100}})
                + "\n",
                encoding="utf-8",
            )

    write_rows_through_8()
    (tmp_path / "09-long-session-v2.jsonl").write_text((diag + "\n") * 14 + json.dumps(
        {"kind": "diagnostic", "data": {"rounds": 1, "input_tokens": 0, "tool_calls": 0}}
    ) + "\n", encoding="utf-8")
    (tmp_path / "09-long-session-v3.jsonl").write_text((diag + "\n") * 15, encoding="utf-8")
    results = tmp_path / "results.json"
    results.write_text(json.dumps({str(i): "PASS" for i in range(1, 10)}), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--dir",
            str(tmp_path),
            "--results",
            str(results),
            "--require-through",
            "9",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "HINT row 9" not in proc.stderr


def test_validate_row9_hint_when_only_quota_blocked_file(tmp_path: Path) -> None:
    for row_id in range(1, 9):
        (tmp_path / f"{row_id:02d}-x.jsonl").write_text(
            json.dumps({"kind": "diagnostic", "data": {"rounds": 1, "input_tokens": 100}}) + "\n",
            encoding="utf-8",
        )
    line_ok = json.dumps(
        {"kind": "diagnostic", "data": {"rounds": 1, "input_tokens": 5000, "tool_calls": 1}}
    )
    line_bad = json.dumps(
        {"kind": "diagnostic", "data": {"rounds": 1, "input_tokens": 0, "tool_calls": 0}}
    )
    (tmp_path / "09-long-session-v2.jsonl").write_text(
        (line_ok + "\n") * 14 + line_bad + "\n",
        encoding="utf-8",
    )
    results = tmp_path / "results.json"
    results.write_text(json.dumps({str(i): "PASS" for i in range(1, 10)}), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--dir",
            str(tmp_path),
            "--results",
            str(results),
            "--require-through",
            "9",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "HINT row 9 (09-long-session-v2.jsonl)" in proc.stderr
    assert "in_last=0" in proc.stderr
