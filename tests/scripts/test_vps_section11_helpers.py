"""Sanity checks for VPS §11 helper scripts (no SSH)."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_vps_section11_helper_scripts_exist_and_executable() -> None:
    names = [
        "section11_agent_api_turn_core.sh",
        "section11_long_session_core.sh",
        "section11_quota_hints.sh",
        "section11_quota_reset_hint.py",
        "mokli_upgrade_section11_status.sh",
        "vps_section11_agent_api_turn.sh",
        "vps_section11_long_session.sh",
        "vps_section11_quota_probe.sh",
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
        "mokli_upgrade_section11_row13_ci.sh",
        "mokli_upgrade_section11_after_pull.sh",
        "mokli_upgrade_p0_turn_estimate.py",
        "mokli_upgrade_p0_live_delta.sh",
        "vps_section11_row13_mobile.sh",
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
    ]
    for name in names:
        path = ROOT / "scripts" / name
        assert path.is_file(), name
        assert path.stat().st_mode & 0o111, f"{name} should be executable"


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
    assert "MOKLI_SECTION11_MODEL" in hints
    assert "free-models-per-day" in hints
    assert "vps_section11_quota_status.sh" in hints


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
    assert "vps_pull_main.sh" in text
    assert "operator-handoff.md" in text
    assert "partial10_ok=" in text
    assert "mokli_upgrade_section11_production_gate.sh" in text
    assert "--require-through 10" in text


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
    assert proc.returncode == 1


def test_post_quota_wires_wait_probe_and_reruns() -> None:
    text = (ROOT / "scripts" / "mokli_upgrade_section11_post_quota.sh").read_text(
        encoding="utf-8"
    )
    assert "wait_quota_reset.sh" in text
    assert "vps_section11_quota_probe.sh" in text
    assert "rerun_partials.sh" in text
    assert "vps_pull_main.sh" in text
    assert "timer_wake.sh" in text


def test_timer_wake_wires_completion_status_after_reset_and_close() -> None:
    text = (ROOT / "scripts" / "mokli_upgrade_section11_timer_wake.sh").read_text(
        encoding="utf-8"
    )
    assert "completion_status.sh" in text
    assert "after_reset_wake.sh" in text
    assert "operator_unblock.sh" in text and "--pull-vps" in text
    assert "close.sh" in text and "--require-through 13" in text
    assert "sync_from_vps.sh" in text and "SECTION11_REQUIRE" in text
    assert "TIMER_WAKE_EXIT" in text
    assert "set -e" in text
    assert "--dry-run" in text


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
    assert "rerun_partials.sh" in text
    assert "remaining_rows.sh" in text
    assert "require-oanda" in text
    assert "vps_section11_row12_desktop.sh" in text


def test_remaining_rows_close_uses_production_gate_pull_vps() -> None:
    text = (ROOT / "scripts" / "mokli_upgrade_section11_remaining_rows.sh").read_text(
        encoding="utf-8"
    )
    assert "production_gate.sh --pull-vps" in text


def test_rerun_partials_syncs_with_pull_vps() -> None:
    text = (ROOT / "scripts" / "mokli_upgrade_section11_rerun_partials.sh").read_text(
        encoding="utf-8"
    )
    assert "sync_from_vps.sh" in text
    assert "--pull-vps" in text
    assert 'section11-results-partial.json" 13' in text or "partial.json\" 13" in text
    assert "vps_section11_row8_fallback_provider.sh" in text


def test_sync_from_vps_supports_pull_vps_flag() -> None:
    text = (ROOT / "scripts" / "mokli_upgrade_section11_sync_from_vps.sh").read_text(
        encoding="utf-8"
    )
    assert "--pull-vps" in text
    assert "MOKLI_SECTION11_VPS_BRANCH" in text
    assert "vps_pull_main.sh" in text


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
