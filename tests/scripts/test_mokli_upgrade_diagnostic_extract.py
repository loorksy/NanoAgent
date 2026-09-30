"""Tests for scripts/mokli_upgrade_diagnostic_extract.py"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "mokli_upgrade_diagnostic_extract.py"


def test_extracts_last_diagnostic_one_liner() -> None:
    lines = [
        json.dumps({"kind": "delta", "data": {"text": "hi"}}),
        json.dumps(
            {
                "kind": "diagnostic",
                "data": {
                    "rounds": 2,
                    "request_input_tokens": 1200,
                    "request_output_tokens": 80,
                    "tool_calls": 1,
                    "context_ms": 40,
                    "model_ms": 900,
                    "tool_ms": 200,
                },
            }
        ),
        json.dumps(
            {
                "kind": "diagnostic",
                "data": {
                    "rounds": 3,
                    "input_tokens": 5000,
                    "output_tokens": 100,
                    "tool_calls": 2,
                    "context_ms": 55,
                    "model_ms": 1100,
                    "tool_ms": 350,
                    "retry_ms": 0,
                    "nested_input_tokens": 800,
                },
            }
        ),
    ]
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input="\n".join(lines),
        capture_output=True,
        text=True,
        check=True,
    )
    out = proc.stdout.strip()
    assert "rounds=3" in out
    assert "in=5000" in out
    assert "tools=2" in out
    assert "nested_in=800" in out
