"""Static wiring for mokli_upgrade_section11_cloud_status.sh."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "mokli_upgrade_section11_cloud_status.sh"


def test_cloud_status_script_wires_scan_fields() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "section11_quota_hints.sh" in text
    assert "section11_prune_row5_stale_no_nested" not in text
    assert "section11_print_cloud_vps_rev" in text
    assert "allow_partial_closure_errors=" in text
    assert "wake_after_buffer_utc" in text
    assert "print-live-rerun-rows" in text
