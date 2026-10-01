"""Sanity checks for VPS §11 helper scripts (no SSH)."""

from __future__ import annotations

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
        "vps_section11_row13_mobile.sh",
    ]
    for name in names:
        path = ROOT / "scripts" / name
        assert path.is_file(), name
        assert path.stat().st_mode & 0o111, f"{name} should be executable"
