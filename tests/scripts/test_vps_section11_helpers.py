"""Sanity checks for VPS §11 helper scripts (no SSH)."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_vps_section11_helper_scripts_exist_and_executable() -> None:
    names = [
        "section11_agent_api_turn_core.sh",
        "section11_long_session_core.sh",
        "mokli_upgrade_section11_status.sh",
        "vps_section11_agent_api_turn.sh",
        "vps_section11_long_session.sh",
        "vps_section11_quota_probe.sh",
        "vps_section11_pull_events.sh",
        "vps_section11_row11_paper.sh",
        "vps_section11_row12_desktop.sh",
        "local_section11_row12_smoke.sh",
        "mokli_upgrade_section11_row13_ci.sh",
        "mokli_upgrade_section11_after_pull.sh",
        "mokli_upgrade_p0_turn_estimate.py",
        "mokli_upgrade_p0_live_delta.sh",
        "vps_section11_row13_mobile.sh",
        "vps_section11_env_check.sh",
        "vps_section11_row1_after_p0.sh",
        "vps_section11_set_oanda_env.sh",
        "mokli_upgrade_section11_production_gate.sh",
        "mokli_upgrade_section11_remaining_rows.sh",
        "vps_pull_main.sh",
    ]
    for name in names:
        path = ROOT / "scripts" / name
        assert path.is_file(), name
        assert path.stat().st_mode & 0o111, f"{name} should be executable"


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
