"""Tests for scripts/mokli_upgrade_p0_live_delta.sh"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "mokli_upgrade_p0_live_delta.sh"


def test_live_delta_extracts_in_token_field(tmp_path: Path) -> None:
    diag = {
        "kind": "diagnostic",
        "data": {
            "rounds": 1,
            "request_input_tokens": 100,
            "nested_input_tokens": 0,
            "provider_tool_count": 11,
            "components": {"final": 5000, "tool_definitions": 2000},
        },
    }
    base = tmp_path / "base.jsonl"
    new = tmp_path / "new.jsonl"
    base.write_text(json.dumps(diag) + "\n", encoding="utf-8")
    diag["data"]["request_input_tokens"] = 80
    diag["data"]["provider_tool_count"] = 3
    diag["data"]["components"] = {"final": 3100, "tool_definitions": 776}
    new.write_text(json.dumps(diag) + "\n", encoding="utf-8")
    proc = subprocess.run(
        ["bash", str(SCRIPT), str(base), str(new)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    assert "in=100" in proc.stdout
    assert "in=80" in proc.stdout
    assert "delta_in=-20" in proc.stdout
    assert "provider_tools=11" in proc.stdout
    assert "provider_tools=3" in proc.stdout
    assert "delta_comp_final=-1900" in proc.stdout


def test_live_delta_quota_probe_without_diagnostic(tmp_path: Path) -> None:
    diag = {
        "kind": "diagnostic",
        "data": {
            "rounds": 1,
            "request_input_tokens": 10934,
            "provider_tool_count": 7,
            "components": {"final": 10271},
        },
    }
    base = tmp_path / "01-no-tools.jsonl"
    probe = tmp_path / "quota-probe.jsonl"
    base.write_text(json.dumps(diag) + "\n", encoding="utf-8")
    probe.write_text(
        json.dumps(
            {
                "kind": "retry",
                "data": {"state": "waiting", "error_kind": "rate_limit", "attempt": 1},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        ["bash", str(SCRIPT), str(base), str(probe)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    assert "in=10934" in proc.stdout
    assert "quota blocked" in proc.stdout
    assert "delta_in=skipped" in proc.stdout


def test_live_delta_skips_numeric_delta_when_new_in_zero(tmp_path: Path) -> None:
    diag = {
        "kind": "diagnostic",
        "data": {
            "rounds": 1,
            "request_input_tokens": 10934,
            "provider_tool_count": 7,
            "components": {"final": 10271},
        },
    }
    probe_diag = {
        "kind": "diagnostic",
        "data": {
            "rounds": 1,
            "request_input_tokens": 0,
            "provider_tool_count": 7,
            "components": {"final": 3603},
        },
    }
    base = tmp_path / "01-no-tools.jsonl"
    probe = tmp_path / "quota-probe.jsonl"
    base.write_text(json.dumps(diag) + "\n", encoding="utf-8")
    probe.write_text(json.dumps(probe_diag) + "\n", encoding="utf-8")
    proc = subprocess.run(
        ["bash", str(SCRIPT), str(base), str(probe)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    assert "in=10934" in proc.stdout
    assert "in=0" in proc.stdout
    assert "delta_in=skipped" in proc.stdout
    assert "delta_in=-" not in proc.stdout
