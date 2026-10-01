"""Tests for mokli_upgrade_section11_after_pull.sh delta hook."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "mokli_upgrade_section11_after_pull.sh"


def _diag(in_t: int, *, provider_tools: int = 3) -> str:
    return json.dumps(
        {
            "kind": "diagnostic",
            "data": {
                "rounds": 1,
                "request_input_tokens": in_t,
                "request_output_tokens": 1,
                "tool_calls": 0,
                "provider_tool_count": provider_tools,
                "components": {"final": 3000 + in_t},
            },
        }
    )


def test_after_pull_runs_p0_delta_when_after_file_exists(tmp_path: Path) -> None:
    events = tmp_path / "events"
    events.mkdir()
    for name, in_t in (
        ("01-no-tools.jsonl", 10000),
        ("01-no-tools-after-p0.jsonl", 3000),
        ("02-single-tool.jsonl", 20000),
    ):
        (events / name).write_text(_diag(in_t) + "\n", encoding="utf-8")
    results = tmp_path / "results.json"
    results.write_text(
        json.dumps({str(i): f"PASS row {i}" for i in range(1, 3)}),
        encoding="utf-8",
    )
    proc = subprocess.run(
        ["bash", str(SCRIPT), str(events), str(results), "2"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    assert "P0 live delta" in proc.stdout
    assert "delta_in=-7000" in proc.stdout
    assert (events / "p0-interim-summary.txt").is_file()


def test_after_pull_interim_when_baseline_only_alt_row1_name(tmp_path: Path) -> None:
    events = tmp_path / "events"
    events.mkdir()
    (events / "01-baseline-alt.jsonl").write_text(_diag(10000) + "\n", encoding="utf-8")
    (events / "quota-probe.jsonl").write_text(_diag(0, provider_tools=7) + "\n", encoding="utf-8")
    (events / "02-single-tool.jsonl").write_text(_diag(20000) + "\n", encoding="utf-8")
    results = tmp_path / "results.json"
    results.write_text(
        json.dumps({str(i): f"PASS row {i}" for i in range(1, 3)}),
        encoding="utf-8",
    )
    proc = subprocess.run(
        ["bash", str(SCRIPT), str(events), str(results), "2"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    assert "P0 interim" in proc.stdout
    assert "01-baseline-alt.jsonl" in proc.stdout or "delta_in=-10000" in proc.stdout


def test_after_pull_runs_interim_delta_from_quota_probe(tmp_path: Path) -> None:
    events = tmp_path / "events"
    events.mkdir()
    (events / "01-no-tools.jsonl").write_text(_diag(10000) + "\n", encoding="utf-8")
    (events / "quota-probe.jsonl").write_text(_diag(0, provider_tools=7) + "\n", encoding="utf-8")
    (events / "02-single-tool.jsonl").write_text(_diag(20000) + "\n", encoding="utf-8")
    results = tmp_path / "results.json"
    results.write_text(
        json.dumps({str(i): f"PASS row {i}" for i in range(1, 3)}),
        encoding="utf-8",
    )
    proc = subprocess.run(
        ["bash", str(SCRIPT), str(events), str(results), "2"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    assert "P0 interim" in proc.stdout
    assert "quota-probe" in proc.stdout
    assert "delta_in=-10000" in proc.stdout


def test_after_pull_interim_survives_quota_probe_without_diagnostic(tmp_path: Path) -> None:
    events = tmp_path / "events"
    events.mkdir()
    (events / "01-no-tools.jsonl").write_text(_diag(10000) + "\n", encoding="utf-8")
    (events / "quota-probe.jsonl").write_text(
        json.dumps(
            {
                "kind": "retry",
                "data": {"state": "waiting", "error_kind": "rate_limit", "attempt": 2},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (events / "02-single-tool.jsonl").write_text(_diag(20000) + "\n", encoding="utf-8")
    results = tmp_path / "results.json"
    results.write_text(
        json.dumps({str(i): f"PASS row {i}" for i in range(1, 3)}),
        encoding="utf-8",
    )
    proc = subprocess.run(
        ["bash", str(SCRIPT), str(events), str(results), "2"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    assert "P0 interim" in proc.stdout
    assert "delta_in=skipped" in proc.stdout
    assert (events / "p0-interim-summary.txt").is_file()
