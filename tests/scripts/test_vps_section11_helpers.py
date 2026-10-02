"""Sanity checks for VPS §11 helper scripts (no SSH)."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_vps_section11_helper_scripts_exist_and_executable() -> None:
    names = [
        "section11_agent_api_turn_core.sh",
        "section11_long_session_core.sh",
        "section11_quota_hints.sh",
        "section11_quota_reset_hint.py",
        "section11_probe_cache_preserve.py",
        "mokli_upgrade_section11_status.sh",
        "vps_section11_agent_api_turn.sh",
        "vps_section11_long_session.sh",
        "vps_section11_quota_probe.sh",
        "vps_section11_quota_gate.sh",
        "vps_section11_quota_status.sh",
        "vps_section11_pull_events.sh",
        "vps_section11_row11_paper.sh",
        "vps_section11_row3_multi_tool.sh",
        "vps_section11_row5_subagents.sh",
        "vps_section11_row9_long_session.sh",
        "vps_section11_row2_single_tool.sh",
        "vps_section11_row10_backtest.sh",
        "mokli_upgrade_section11_rerun_partials.sh",
        "mokli_upgrade_section11_blockers.sh",
        "mokli_upgrade_section11_validate.sh",
        "mokli_upgrade_section11_sync_from_vps.sh",
        "vps_section11_row4_gold_analysis.sh",
        "vps_section11_row6_tool_failure.sh",
        "vps_section11_row7_retry.sh",
        "vps_section11_row8_fallback_provider.sh",
        "vps_section11_row12_desktop.sh",
        "local_section11_row12_smoke.sh",
        "mokli_upgrade_section11_precheck_ui.sh",
        "mokli_upgrade_section11_row13_ci.sh",
        "mokli_upgrade_section11_after_pull.sh",
        "mokli_upgrade_p0_turn_estimate.py",
        "mokli_upgrade_p0_live_delta.sh",
        "vps_section11_row13_mobile.sh",
        "vps_section11_scp_branch_scripts.sh",
        "vps_section11_env_check.sh",
        "vps_section11_row1_after_p0.sh",
        "vps_section11_row1_greeting.sh",
        "vps_section11_set_oanda_env.sh",
        "mokli_upgrade_section11_production_gate.sh",
        "mokli_upgrade_section11_remaining_rows.sh",
        "vps_pull_main.sh",
        "vps_section11_fix_events_ownership.sh",
        "mokli_upgrade_section11_cloud_status.sh",
        "mokli_upgrade_aggregate_pytest.sh",
        "mokli_upgrade_section11_operator_unblock.sh",
        "mokli_upgrade_section11_wait_quota_reset.sh",
        "mokli_upgrade_section11_post_quota.sh",
        "mokli_upgrade_section11_after_reset_wake.sh",
        "mokli_upgrade_section11_completion_status.sh",
        "mokli_upgrade_section11_timer_wake.sh",
        "mokli_upgrade_section11_try_row11_paper.sh",
        "mokli_upgrade_section11_check_wake.sh",
        "mokli_upgrade_section11_monitor_log.sh",
        "mokli_upgrade_section11_monitor_loop.sh",
        "mokli_upgrade_section11_sync_cloud_branch.sh",
    ]
    for name in names:
        path = ROOT / "scripts" / name
        assert path.is_file(), name
        assert path.stat().st_mode & 0o111, f"{name} should be executable"


def test_quota_hints_exports_wake_after_buffer_helper() -> None:
    text = (ROOT / "scripts" / "section11_quota_hints.sh").read_text(encoding="utf-8")
    assert "section11_emit_wake_after_buffer" in text
    assert "section11_parse_probe_in" in text
    assert "section11_allow_partial_closure_errors" in text
    assert "section11_wake_log_current_run" in text
    assert "section11_prune_quota_failed_output" in text
    assert "section11_prune_row5_stale_no_nested" in text


def test_sync_cloud_branch_script_ff_only() -> None:
    text = (
        ROOT / "scripts" / "mokli_upgrade_section11_sync_cloud_branch.sh"
    ).read_text(encoding="utf-8")
    assert "CLOUD_PULL_OK" in text
    assert "pull --ff-only" in text


def test_scp_branch_scripts_includes_row5_and_diagnostic_extract() -> None:
    text = (ROOT / "scripts" / "vps_section11_scp_branch_scripts.sh").read_text(
        encoding="utf-8"
    )
    assert "mokli_upgrade_diagnostic_extract.py" in text
    assert "mokli_upgrade_section11_blockers.sh" in text
    assert "mokli_upgrade_section11_close.sh" in text
    assert "vps_section11_row5_subagents.sh" in text
    assert "vps_section11_env_check.sh" in text
    assert "mokli_upgrade_section11_validate.sh" in text
    assert "mokli_upgrade_section11_after_reset_wake.sh" in text
    assert "mokli_upgrade_section11_operator_unblock.sh" in text
    assert text.count('scripts/') >= 13


def test_prune_skips_quota_probe_filenames(tmp_path: Path) -> None:
    probe = tmp_path / "quota-probe.jsonl"
    probe.write_text(
        '{"kind": "diagnostic", "data": {"rounds": 1, "input_tokens": 0}}\n',
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            "bash",
            "-c",
            f'source "{ROOT}/scripts/section11_quota_hints.sh" && '
            f'section11_prune_quota_failed_output "{tmp_path}" "quota-probe.jsonl" "{ROOT}"',
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert probe.is_file()


def test_prune_quota_failed_output_removes_in_zero_jsonl(tmp_path: Path) -> None:
    stale = tmp_path / "05-subagents-v2.jsonl"
    stale.write_text(
        '{"kind": "diagnostic", "data": {"rounds": 1, "input_tokens": 0}}\n',
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            "bash",
            "-c",
            f'source "{ROOT}/scripts/section11_quota_hints.sh" && '
            f'section11_prune_quota_failed_output "{tmp_path}" "05-subagents-v2.jsonl" "{ROOT}"',
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert not stale.is_file()
    assert "quota-failed" in proc.stderr


def test_prune_quota_failed_keeps_row_jsonl_with_rate_limit_when_in_gt_zero(
    tmp_path: Path,
) -> None:
    """Row 7-style JSONL may mention rate_limit while diagnostic in>0."""
    path = tmp_path / "07-retry.jsonl"
    path.write_text(
        '{"kind":"status","data":{"summary":"Rate limit exceeded, waiting"}}\n'
        + json.dumps(
            {
                "kind": "diagnostic",
                "data": {"rounds": 1, "input_tokens": 10931, "tool_calls": 0},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            "bash",
            "-c",
            f'source "{ROOT}/scripts/section11_quota_hints.sh" && '
            f'section11_prune_quota_failed_output "{tmp_path}" "07-retry.jsonl" "{ROOT}"',
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert path.is_file()
    assert "quota-failed" not in proc.stderr


def test_prune_quota_failed_keeps_row5_jsonl_when_in_gt_zero_nested_in_zero(
    tmp_path: Path,
) -> None:
    """Regression: parse must not treat nested_in=0 as top-level in=0."""
    path = tmp_path / "05-subagents-v2.jsonl"
    path.write_text(
        json.dumps(
            {
                "kind": "diagnostic",
                "data": {
                    "rounds": 4,
                    "input_tokens": 51744,
                    "output_tokens": 100,
                    "tool_calls": 4,
                    "nested_rounds": 0,
                    "nested_input_tokens": 0,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            "bash",
            "-c",
            f'source "{ROOT}/scripts/section11_quota_hints.sh" && '
            f'section11_prune_quota_failed_output "{tmp_path}" "05-subagents-v2.jsonl" "{ROOT}"',
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert path.is_file()
    assert "quota-failed" not in proc.stderr


def test_validate_at_13_does_not_delete_stale_row5_jsonl(tmp_path: Path) -> None:
    stale = tmp_path / "05-subagents.jsonl"
    stale.write_text(
        '{"kind":"tool","data":{"name":"spawn","event":"failed",'
        '"summary":"code": 429, rate-limited upstream"}}\n'
        '{"kind":"diagnostic","data":{"rounds":4,"input_tokens":51744,'
        '"tool_calls":4,"nested_rounds":0}}\n',
        encoding="utf-8",
    )
    results = tmp_path / "results.json"
    results.write_text(json.dumps({str(i): "PASS" for i in range(1, 14)}), encoding="utf-8")
    for row_id in range(1, 14):
        if row_id == 5:
            continue
        (tmp_path / f"{row_id:02d}-stub.jsonl").write_text(
            json.dumps(
                {
                    "kind": "diagnostic",
                    "data": {"rounds": 1, "input_tokens": 100, "tool_calls": 2},
                }
            )
            + "\n",
            encoding="utf-8",
        )
    (tmp_path / "01-no-tools-after-p0.jsonl").write_text(
        json.dumps({"kind": "diagnostic", "data": {"rounds": 1, "input_tokens": 100}})
        + "\n",
        encoding="utf-8",
    )
    validate_sh = ROOT / "scripts" / "mokli_upgrade_section11_validate.sh"
    proc = subprocess.run(
        [
            "bash",
            str(validate_sh),
            "--dir",
            str(tmp_path),
            "--results",
            str(results),
            "--require-through",
            "13",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert stale.is_file(), proc.stderr
    assert proc.returncode == 1
    assert "Row 5 diagnostic needs nested_rounds" in proc.stderr


def test_prune_row5_stale_removes_spawn_429_no_nested(tmp_path: Path) -> None:
    stale = tmp_path / "05-subagents.jsonl"
    stale.write_text(
        '{"kind":"tool","data":{"name":"spawn","event":"failed","summary":"429 upstream"}}\n'
        + '{"kind": "diagnostic", "data": {"rounds": 4, "input_tokens": 50000, '
        '"nested_rounds": 0}}\n',
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            "bash",
            "-c",
            f'source "{ROOT}/scripts/section11_quota_hints.sh" && '
            f'section11_prune_row5_stale_no_nested "{tmp_path}" "{ROOT}"',
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert not stale.is_file()
    assert "stale 05-subagents.jsonl" in proc.stderr


def test_parse_probe_in_ignores_nested_in_zero() -> None:
    proc = subprocess.run(
        [
            "bash",
            "-c",
            'source scripts/section11_quota_hints.sh; section11_parse_probe_in '
            '"rounds=1 in=4058 out=31 nested_in=0"',
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.stdout.strip() == "4058"


def test_allow_partial_closure_errors_matches_validate() -> None:
    events = ROOT / "section11-events"
    results = ROOT / "section11-results-partial.json"
    if not events.is_dir() or not results.is_file():
        pytest.skip("section11-events pack not present")
    py = ROOT / ".venv/bin/python"
    if not py.is_file():
        py = Path("python3")
    validate = ROOT / "scripts/mokli_upgrade_section11_validate.py"
    proc = subprocess.run(
        [
            "bash",
            "-c",
            f'source "{ROOT}/scripts/section11_quota_hints.sh" && '
            f'section11_allow_partial_closure_errors "{py}" "{validate}" '
            f'"{events}" "{results}" 13',
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    helper_val = proc.stdout.strip()
    direct = subprocess.run(
        [
            str(py),
            str(validate),
            "--dir",
            str(events),
            "--results",
            str(results),
            "--require-through",
            "13",
            "--allow-partial",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    m = re.search(r"^closure_errors=(\d+)", direct.stderr, re.MULTILINE)
    assert m, direct.stderr
    assert helper_val == m.group(1)


def test_parse_probe_in_ignores_nested_in_on_multi_round_row() -> None:
    proc = subprocess.run(
        [
            "bash",
            "-c",
            'source scripts/section11_quota_hints.sh; section11_parse_probe_in '
            '"rounds=4 in=51744 out=1218 tools=4 nested_in=0"',
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.stdout.strip() == "51744"


def test_env_check_mentions_section11_model_when_quota_hinted() -> None:
    text = (ROOT / "scripts" / "vps_section11_env_check.sh").read_text(encoding="utf-8")
    assert "MOKLI_SECTION11_MODEL" in text
    assert "llm_quota blocked" in text
    assert "vps_section11_quota_status.sh" in text
    assert "grep -E '^(probe=|QUOTA_" in text
    assert "REQUIRE_QUOTA" in text and "quota_probe.sh" in text
    assert "gateway_model_preset=" in text
    assert "git_branch=" in text
    assert "MOKLI_SECTION11_VPS_BRANCH" in text
    assert "VPS git_rev=" in text and "local_rev" in text
    assert "rev-parse --short=7" in text
    assert "oanda_env_file=" in text
    assert "vps_section11_set_oanda_env.sh" in text
    assert "_read_gateway_model_preset" in text
    assert "sudo -u" in text


def test_row12_local_smoke_prefers_dev_vite_url() -> None:
    text = (ROOT / "scripts" / "local_section11_row12_smoke.sh").read_text(encoding="utf-8")
    assert "127.0.0.1:5173" in text
    assert "MOKLI_UI_URL" in text
    assert "8766" in text


def test_jsonl_retry_rate_limit_counts_as_quota_block(tmp_path: Path) -> None:
    probe = tmp_path / "quota-probe.jsonl"
    probe.write_text(
        '{"kind":"retry","data":{"error_kind":"rate_limit","state":"waiting"}}\n',
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            "bash",
            "-c",
            f'source "{ROOT}/scripts/section11_quota_hints.sh" && '
            f'section11_jsonl_indicates_quota_block "{probe}"',
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0


def test_quota_probe_sources_unblock_hints() -> None:
    probe = (ROOT / "scripts" / "vps_section11_quota_probe.sh").read_text(encoding="utf-8")
    hints = (ROOT / "scripts" / "section11_quota_hints.sh").read_text(encoding="utf-8")
    assert "section11_quota_hints.sh" in probe
    assert "section11_print_quota_unblock_hints" in probe
    assert "section11_pull_probe_to_workspace" in probe
    assert "incomplete probe pulled" in probe
    assert "section11_probe_cache_preserve.py" in probe
    assert "MOKLI_SECTION11_MODEL" in hints
    assert "free-models-per-day" in hints
    assert "vps_section11_quota_status.sh" in hints
    assert "section11_print_cloud_vps_rev" in hints


def test_agent_api_turn_forwards_section11_model_over_ssh() -> None:
    turn = (ROOT / "scripts" / "vps_section11_agent_api_turn.sh").read_text(encoding="utf-8")
    long_sess = (ROOT / "scripts" / "vps_section11_long_session.sh").read_text(encoding="utf-8")
    assert "vps_ssh env MOKLI_SECTION11_MODEL" in turn
    assert "vps_ssh env MOKLI_SECTION11_MODEL" in long_sess


def test_vps_pull_main_waits_gateway_and_agent_api() -> None:
    text = (ROOT / "scripts" / "vps_pull_main.sh").read_text(encoding="utf-8")
    assert "18791/health" in text
    assert "8766/api/v2/health" in text
    assert "API_OK" in text and "GW_OK" in text
    assert "section11-events" in text
    assert "MOKLI_SECTION11_VPS_BRANCH" in text
    assert "§11 closure may need" in text


def test_row9_long_session_prompt_uses_list_dir_only() -> None:
    text = (ROOT / "scripts" / "vps_section11_row9_long_session.sh").read_text(
        encoding="utf-8"
    )
    prompt_line = next(line for line in text.splitlines() if "PROMPT=" in line)
    assert "list_dir" in prompt_line
    assert "get_gold_quote" in prompt_line and "Do not call get_gold_quote" in prompt_line


def test_row5_subagents_prompt_fetch_evidence_before_spawn() -> None:
    text = (ROOT / "scripts" / "vps_section11_row5_subagents.sh").read_text(
        encoding="utf-8"
    )
    prompt_line = next(line for line in text.splitlines() if "PROMPT=" in line)
    assert "call fetch_evidence" in prompt_line and "Then spawn" in prompt_line
    assert prompt_line.index("call fetch_evidence") < prompt_line.index("Then spawn")


def test_row3_multi_tool_prompt_lists_dir_before_gold() -> None:
    text = (ROOT / "scripts" / "vps_section11_row3_multi_tool.sh").read_text(
        encoding="utf-8"
    )
    assert "list_dir" in text and "get_gold_quote" in text
    prompt_line = next(line for line in text.splitlines() if "PROMPT=" in line)
    assert prompt_line.index("list_dir") < prompt_line.index("get_gold_quote")


def test_section11_turn_core_retries_session_create() -> None:
    text = (ROOT / "scripts" / "section11_agent_api_turn_core.sh").read_text(
        encoding="utf-8"
    )
    assert "for _try in" in text
    assert "failed to create session" in text


def test_section11_turn_core_reexecs_as_service_user_when_root() -> None:
    turn = (ROOT / "scripts" / "section11_agent_api_turn_core.sh").read_text(
        encoding="utf-8"
    )
    long = (ROOT / "scripts" / "section11_long_session_core.sh").read_text(
        encoding="utf-8"
    )
    assert "SECTION11_TURN_AS_USER" in turn
    assert "sudo -u" in turn and 'id -un)" != "$SERVICE_USER"' in turn
    assert "SECTION11_LONG_AS_USER" in long


def test_operator_unblock_script_wires_probe_and_blockers() -> None:
    text = (ROOT / "scripts" / "mokli_upgrade_section11_operator_unblock.sh").read_text(
        encoding="utf-8"
    )
    assert "vps_section11_quota_probe.sh" in text
    assert "vps_section11_quota_status.sh" in text
    assert "--skip-probe" in text
    assert "mokli_upgrade_section11_blockers.sh" in text
    assert "mokli_upgrade_section11_post_quota.sh" in text
    assert "timer_wake.sh --wait-quota" in text
    assert "vps_section11_set_oanda_env.sh" in text
    assert "--pull-vps" in text
    assert "--sync-vps-rev" in text
    assert "operator-handoff.md" in text
    assert "partial10_ok=" in text
    assert "mokli_upgrade_section11_production_gate.sh" in text
    assert "--require-through 10" in text
    assert "live_rerun_rows=" in text
    assert "print-live-rerun-rows" in text
    assert "sync_cloud_branch.sh" in text
    assert "allow_partial_closure_errors=" in text
    assert "wake_after_buffer_utc=" in text
    assert "section11_prune_row5_stale_no_nested" not in text
    assert "section11_print_cloud_vps_rev" in text


def test_operator_unblock_skip_probe_reports_partial10_when_pack_present() -> None:
    partial = ROOT / "section11-results-partial.json"
    events = ROOT / "section11-events"
    if not partial.is_file() or not events.is_dir():
        return
    script = ROOT / "scripts" / "mokli_upgrade_section11_operator_unblock.sh"
    proc = subprocess.run(
        ["bash", str(script), "--skip-probe"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )
    combined = proc.stdout + proc.stderr
    assert "OPERATOR_UNBLOCK_EXIT=1" in combined
    assert "partial10_ok=1" in combined
    assert "partial10_gate=1" in combined
    assert "wake_after_buffer_utc=" in combined
    assert "seconds_until_reset=" in combined
    assert "live_rerun_rows=" in combined
    assert "allow_partial_closure_errors=2" in combined
    assert proc.returncode == 1


def test_monitor_log_syncs_vps_rev_via_check_wake() -> None:
    text = (ROOT / "scripts" / "mokli_upgrade_section11_monitor_log.sh").read_text(
        encoding="utf-8"
    )
    assert "--sync-vps-rev" in text
    assert "timer_wake_wait_quota.log" in text
    assert "WAIT_HEARTBEAT" in text


def test_check_wake_script_reports_tmux_and_log() -> None:
    script = ROOT / "scripts" / "mokli_upgrade_section11_check_wake.sh"
    assert script.is_file() and script.stat().st_mode & 0o111
    text = script.read_text(encoding="utf-8")
    assert "section11-timer-wake-wait" in text
    assert "timer_wake_wait_quota.log" in text
    assert "mokli_upgrade_section11_blockers.sh" in text
    assert "section11_emit_wake_after_buffer" in text
    assert "WAIT_HEARTBEAT" in text
    assert "section11-monitor-loop" in text
    assert "section11_print_cloud_vps_rev" in text
    assert "section11_wake_log_current_run" in text
    assert "Started timer_wake" in text
    assert "--sync-vps-rev" in text
    assert "vps_pull_main.sh" in text


def test_check_wake_prints_wake_eta_when_reset_known() -> None:
    probe = ROOT / "section11-events" / "quota-probe.jsonl"
    if not probe.is_file():
        return
    script = ROOT / "scripts" / "mokli_upgrade_section11_check_wake.sh"
    proc = subprocess.run(
        ["bash", str(script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    combined = proc.stdout + proc.stderr
    assert proc.returncode == 0
    assert "wake_after_buffer_sec=" in combined
    if "seconds_until_reset=unknown" not in combined:
        assert "wake_after_buffer_utc=" in combined


def test_post_quota_wires_wait_probe_and_reruns() -> None:
    text = (ROOT / "scripts" / "mokli_upgrade_section11_post_quota.sh").read_text(
        encoding="utf-8"
    )
    assert "sync_cloud_branch.sh" in text
    assert "wait_quota_reset.sh" in text
    assert "vps_section11_quota_probe.sh" in text
    assert "rerun_partials.sh" in text
    assert "mokli_upgrade_section11_try_row11_paper.sh" in text
    assert "--sync-vps-rev" in text
    assert "timer_wake.sh" in text
    assert "mokli_upgrade_section11_blockers.sh" in text


def test_timer_wake_wires_completion_status_after_reset_and_close() -> None:
    text = (ROOT / "scripts" / "mokli_upgrade_section11_timer_wake.sh").read_text(
        encoding="utf-8"
    )
    assert "completion_status.sh" in text
    assert "after_reset_wake.sh" in text
    assert "operator_unblock.sh" in text and "--pull-vps" in text
    assert "close.sh" in text and "--require-through 13" in text
    assert '--results "$SECTION11_RESULTS"' in text
    assert "sync_from_vps.sh" in text and "SECTION11_REQUIRE" in text
    assert "TIMER_WAKE_EXIT" in text
    assert "set -e" in text
    assert "--dry-run" in text
    assert "remaining_rows.sh prints the row 11" in text
    assert "mokli_upgrade_section11_try_row11_paper.sh" in text


def test_completion_status_cached_quota_no_live_gate_by_default() -> None:
    text = (ROOT / "scripts" / "mokli_upgrade_section11_completion_status.sh").read_text(
        encoding="utf-8"
    )
    assert "completion_status:" in text
    assert "SECTION11_COMPLETION_EXIT" in text
    assert "--live-gate" in text
    assert "operator_unblock.sh --pull-vps" in text
    assert "blockers.sh" in text and "--skip-vps" in text


def test_quota_status_ssh_path_treats_rate_limit_before_invalid() -> None:
    text = (ROOT / "scripts" / "vps_section11_quota_status.sh").read_text(encoding="utf-8")
    assert "(no diagnostic; rate limit)" in text
    start = text.index("vps_ssh bash")
    end = text.index("\nEOS\n", start)
    ssh = text[start:end]
    assert ssh.index("rate_limit") < ssh.index("INVALID probe")


def test_after_reset_wake_probe_without_long_wait() -> None:
    text = (ROOT / "scripts" / "mokli_upgrade_section11_after_reset_wake.sh").read_text(
        encoding="utf-8"
    )
    assert "wait_quota_reset.sh --wait" not in text
    assert "vps_section11_quota_probe.sh" in text
    assert "VPS git vs Cloud (post-pull)" in text
    assert "rerun_partials.sh" in text
    assert "remaining_rows.sh" in text
    assert "require-oanda" in text
    assert "vps_section11_row12_desktop.sh" in text
    assert "mokli_upgrade_section11_try_row11_paper.sh" in text
    assert "section11-results-partial.json" in text
    assert "mokli_upgrade_section11_blockers.sh" in text
    assert "blockers remain" in text


def test_try_row11_paper_skips_without_quota_or_oanda() -> None:
    script = ROOT / "scripts" / "mokli_upgrade_section11_try_row11_paper.sh"
    proc = subprocess.run(
        ["bash", str(script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert proc.returncode == 0
    assert "SKIP §11 row 11" in proc.stderr or "SKIP §11 row 11" in proc.stdout


def test_remaining_rows_close_uses_production_gate_pull_vps() -> None:
    text = (ROOT / "scripts" / "mokli_upgrade_section11_remaining_rows.sh").read_text(
        encoding="utf-8"
    )
    assert "mokli_upgrade_section11_blockers.sh" in text
    assert "production_gate.sh --pull-vps" in text


def test_rerun_partials_syncs_with_pull_vps() -> None:
    text = (ROOT / "scripts" / "mokli_upgrade_section11_rerun_partials.sh").read_text(
        encoding="utf-8"
    )
    assert "sync_from_vps.sh" in text
    assert "--pull-vps" in text
    assert 'section11-results-partial.json" 13' in text or "partial.json\" 13" in text
    assert "vps_section11_row8_fallback_provider.sh" in text
    assert "print-live-rerun-rows" in text
    assert "section11_prune_row5_stale_no_nested" in text


def test_sync_from_vps_supports_pull_vps_flag() -> None:
    text = (ROOT / "scripts" / "mokli_upgrade_section11_sync_from_vps.sh").read_text(
        encoding="utf-8"
    )
    assert "--pull-vps" in text
    assert "MOKLI_SECTION11_VPS_BRANCH" in text
    assert "vps_pull_main.sh" in text
    assert "section11_prune_row5_stale_no_nested" not in text
    assert 'REQUIRE="${POSITIONAL[2]:-13}"' in text
    assert "sync_summary:" in text
    assert "INCOMPLETE sync from VPS" in text
    assert "not @13" in text


def test_gitignore_excludes_mistaken_at13_events_dir() -> None:
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "/@13/" in text


def test_wait_quota_reset_long_sleep_emits_heartbeats() -> None:
    text = (ROOT / "scripts" / "mokli_upgrade_section11_wait_quota_reset.sh").read_text(
        encoding="utf-8"
    )
    assert "WAIT_HEARTBEAT" in text
    assert "chunk_sec" in text


def test_wait_quota_reset_dry_run_on_fixture_probe() -> None:
    probe = ROOT / "section11-events" / "quota-probe.jsonl"
    if not probe.is_file():
        return
    script = ROOT / "scripts" / "mokli_upgrade_section11_wait_quota_reset.sh"
    proc = subprocess.run(
        ["bash", str(script), "--probe", str(probe)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    assert "seconds_until_reset=" in proc.stdout
    assert "OpenRouter" in proc.stderr


def test_runbook_close_apply_at_13_documents_partial_results() -> None:
    runbooks = [
        "mokli_upgrade_section11_remaining_rows.sh",
        "mokli_upgrade_section11_post_quota.sh",
        "mokli_upgrade_section11_rerun_partials.sh",
        "mokli_upgrade_section11_operator_unblock.sh",
        "mokli_upgrade_section11_cloud_status.sh",
        "mokli_upgrade_section11_timer_wake.sh",
        "local_section11_row12_smoke.sh",
        "mokli_upgrade_section11_precheck_ui.sh",
        "mokli_upgrade_preflight.sh",
        "mokli_upgrade_section11_sync_from_vps.sh",
    ]
    for name in runbooks:
        text = (ROOT / "scripts" / name).read_text(encoding="utf-8")
        assert "mokli_upgrade_section11_close.sh" in text or "section11_close.sh" in text, name
        assert "--apply" in text and "--require-through" in text, name
        assert (
            "section11-results-partial.json" in text or "SECTION11_RESULTS" in text
        ), name


def test_vps_pull_main_rejects_extra_positional_args() -> None:
    script = ROOT / "scripts" / "vps_pull_main.sh"
    proc = subprocess.run(
        ["bash", str(script), "main", "extra"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 2
    assert "Usage" in proc.stderr
