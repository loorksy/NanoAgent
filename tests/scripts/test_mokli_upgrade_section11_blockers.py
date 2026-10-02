"""Tests for scripts/mokli_upgrade_section11_blockers.sh"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "mokli_upgrade_section11_blockers.sh"


def test_blockers_skip_vps_prints_local_cached_quota(tmp_path: Path) -> None:
    events = tmp_path / "events"
    events.mkdir()
    (events / "01-no-tools.jsonl").write_text(
        json.dumps({"kind": "diagnostic", "data": {"rounds": 1, "input_tokens": 1}}) + "\n",
        encoding="utf-8",
    )
    (events / "quota-probe.jsonl").write_text(
        json.dumps({"kind": "diagnostic", "data": {"rounds": 1, "input_tokens": 0}}) + "\n",
        encoding="utf-8",
    )
    results = tmp_path / "results.json"
    results.write_text(json.dumps({"1": "PASS"}), encoding="utf-8")
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--skip-vps", "--require-through", "1", str(events), str(results)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert "cached LLM quota" in proc.stdout
    assert "QUOTA_BLOCKED" in proc.stdout or "QUOTA_BLOCKED" in proc.stderr


def test_blockers_exit_one_on_partial_pack_skip_vps(tmp_path: Path) -> None:
    partial = ROOT / "section11-results-partial.json"
    if not partial.is_file():
        payload = {str(i): "PASS" for i in range(1, 11)}
        payload.update({11: "", 12: "", 13: ""})
        partial = tmp_path / "results.json"
        partial.write_text(json.dumps(payload), encoding="utf-8")
    events = ROOT / "section11-events"
    if not events.is_dir():
        events = tmp_path / "events"
        events.mkdir()
        (events / "01-no-tools.jsonl").write_text(
            json.dumps({"kind": "diagnostic", "data": {"rounds": 1, "input_tokens": 1}}) + "\n",
            encoding="utf-8",
        )
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--skip-vps", str(events), str(partial)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert proc.returncode == 1
    assert "BLOCKERS_EXIT=1" in proc.stderr
    assert "BLOCKED" in proc.stderr or "BLOCKED" in proc.stdout
    assert "skip-vps" in proc.stdout.lower() or "skipped" in proc.stdout.lower()
    assert "NEXT §11" in proc.stderr
    combined = proc.stdout + proc.stderr
    if partial.name == "section11-results-partial.json":
        assert "PARTIAL" in combined
        assert "rerun_partials" in combined
        assert "timer_wake.sh --wait-quota" in combined
        after_p0 = events / "01-no-tools-after-p0.jsonl"
        if after_p0.is_file():
            assert "NEXT P0:" not in combined
        else:
            assert "01-no-tools-after-p0.jsonl" in combined
        assert "closure_errors=" in combined
        assert "blockers_summary:" in combined
        assert "live_rerun_rows=" in combined
        assert combined.count("closure_errors=") >= 1
        if (ROOT / "section11-events" / "quota-probe.jsonl").is_file():
            assert "HINT reset:" in combined


def test_blockers_require_through_ten_can_pass_skip_vps() -> None:
    events = ROOT / "section11-events"
    partial = ROOT / "section11-results-partial.json"
    if not events.is_dir() or not partial.is_file():
        return
    proc = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--skip-vps",
            "--require-through",
            "10",
            str(events),
            str(partial),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert "BLOCKERS_EXIT=0" in proc.stdout
    assert "require-through 10" in proc.stdout


def test_blockers_script_hints_after_p0_in_gt_zero() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "01-no-tools-after-p0.jsonl" in text
    assert "needs live in>0" in text
    assert "ENV_COMBINED" in text
    assert "NEXT OANDA:" in text
    assert "oanda_env_file" in text
    assert "NEXT quota:" in text
    assert "section11_parse_probe_in" in text


def test_blockers_closure_errors_matches_validate_on_partial_at_13() -> None:
    events = ROOT / "section11-events"
    partial = ROOT / "section11-results-partial.json"
    validate = ROOT / "scripts" / "mokli_upgrade_section11_validate.sh"
    if not events.is_dir() or not partial.is_file():
        return
    proc_v = subprocess.run(
        [
            "bash",
            str(validate),
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
    combined_v = proc_v.stdout + proc_v.stderr
    match_v = re.search(r"closure_errors=(\d+)", combined_v)
    assert proc_v.returncode != 0
    assert match_v, combined_v[-500:]
    err_count = int(match_v.group(1))
    assert err_count >= 1
    proc_b = subprocess.run(
        ["bash", str(SCRIPT), "--skip-vps", "--require-through", "13", str(events), str(partial)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    combined_b = proc_b.stdout + proc_b.stderr
    match = re.search(r"closure_errors=(\d+)", combined_b)
    assert match, combined_b[-800:]
    assert int(match.group(1)) == err_count
    assert "blockers_summary:" in combined_b
    assert "seconds_until_reset=" in combined_b


def test_blockers_next_p0_on_partial_pack_require_13() -> None:
    events = ROOT / "section11-events"
    partial = ROOT / "section11-results-partial.json"
    if not events.is_dir() or not partial.is_file():
        return
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--skip-vps", "--require-through", "13", str(events), str(partial)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert proc.returncode == 1
    after_p0 = events / "01-no-tools-after-p0.jsonl"
    if after_p0.is_file():
        assert "NEXT P0:" not in proc.stderr
    else:
        assert "NEXT P0:" in proc.stderr


def test_blockers_uses_validate_shell_wrapper() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "mokli_upgrade_section11_validate.sh" in text
    assert "print-live-rerun-rows" in text
    assert text.count("mokli_upgrade_section11_validate.py") == 1


def test_blockers_help() -> None:
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--help"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 2
    assert "Usage" in proc.stderr
