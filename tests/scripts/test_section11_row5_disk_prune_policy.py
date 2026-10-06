"""§11 row-5 JSONL: disk prune only before live VPS turns, not in status/validate."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"

NO_DISK_PRUNE = (
    "mokli_upgrade_section11_blockers.sh",
    "mokli_upgrade_section11_close.sh",
    "mokli_upgrade_section11_cloud_status.sh",
    "mokli_upgrade_section11_completion_status.sh",
    "mokli_upgrade_section11_operator_unblock.sh",
    "mokli_upgrade_section11_sync_from_vps.sh",
    "mokli_upgrade_section11_validate.sh",
    "mokli_upgrade_section11_production_gate.sh",
)

PRUNE_BEFORE_LIVE_TURN = (
    "mokli_upgrade_section11_rerun_partials.sh",
    "vps_section11_row5_subagents.sh",
)


@pytest.mark.parametrize("script_name", NO_DISK_PRUNE)
def test_status_scripts_do_not_prune_row5_jsonl_on_disk(script_name: str) -> None:
    text = (SCRIPTS / script_name).read_text(encoding="utf-8")
    assert "section11_prune_row5_stale_no_nested" not in text, script_name


@pytest.mark.parametrize("script_name", PRUNE_BEFORE_LIVE_TURN)
def test_live_turn_scripts_prune_stale_row5_before_llm(script_name: str) -> None:
    text = (SCRIPTS / script_name).read_text(encoding="utf-8")
    assert "section11_prune_row5_stale_no_nested" in text, script_name
