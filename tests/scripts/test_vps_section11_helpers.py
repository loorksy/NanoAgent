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
    assert "REQUIRE_QUOTA" in text and "quota_probe.sh" in text
    assert "gateway_model_preset=" in text
    assert "_read_gateway_model_preset" in text
    assert "sudo -u" in text


def test_quota_probe_sources_unblock_hints() -> None:
    probe = (ROOT / "scripts" / "vps_section11_quota_probe.sh").read_text(encoding="utf-8")
    hints = (ROOT / "scripts" / "section11_quota_hints.sh").read_text(encoding="utf-8")
    assert "section11_quota_hints.sh" in probe
    assert "section11_print_quota_unblock_hints" in probe
    assert "MOKLI_SECTION11_MODEL" in hints


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
