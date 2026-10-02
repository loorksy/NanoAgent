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


def test_extracts_turn_diagnostics_to_dict_wire_format() -> None:
    """§11 JSONL should match pipe/gateway: kind diagnostic + TurnDiagnostics.to_dict()."""
    from mokli.agent.turn_diagnostics import TurnDiagnostics

    diag = TurnDiagnostics(model="anthropic/claude-opus-4-5", provider="anthropic")
    diag.rounds = 2
    diag.input_tokens = 4000
    diag.output_tokens = 120
    diag.nested_input_tokens = 900
    diag.tool_calls = 1
    diag.context_ms = 35
    diag.model_ms = 800
    diag.tool_ms = 150
    diag.retry_ms = 100
    wire = json.dumps({"kind": "diagnostic", "data": diag.to_dict()})
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=wire,
        capture_output=True,
        text=True,
        check=True,
    )
    out = proc.stdout.strip()
    assert "rounds=2" in out
    assert "in=4900" in out  # input + nested_input
    assert "out=120" in out
    assert "tools=1" in out
    assert "ctx_ms=35" in out
    assert "retry_ms=100" in out
    assert "nested_in=900" in out


def test_extracts_sse_data_prefix_line() -> None:
    """Operator handoff: ``grep '^data: ' … | sed 's/^data: //'`` before extract."""
    event = {
        "id": "e2",
        "session": "s",
        "run": "r",
        "ts": 2,
        "kind": "diagnostic",
        "data": {"rounds": 2, "request_input_tokens": 300, "tool_calls": 1},
    }
    line = "data: " + json.dumps(event)
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=line,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "rounds=2" in proc.stdout
    assert "in=300" in proc.stdout


def test_extracts_agent_api_gateway_event_shape() -> None:
    """Agent API SSE ``data:`` lines are full GatewayEvent objects."""
    event = {
        "id": "evt-1",
        "session": "sess-1",
        "run": "run-1",
        "ts": 1,
        "kind": "diagnostic",
        "data": {
            "rounds": 1,
            "request_input_tokens": 777,
            "request_output_tokens": 11,
            "tool_calls": 0,
        },
    }
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        check=True,
    )
    assert "rounds=1" in proc.stdout
    assert "in=777" in proc.stdout


def test_one_liner_includes_p0_fold_metrics_when_nonzero() -> None:
    payload = {
        "kind": "diagnostic",
        "data": {
            "rounds": 5,
            "request_input_tokens": 2000,
            "request_output_tokens": 50,
            "tool_calls": 3,
            "referenced_chars_saved": 12000,
            "folded_candle_chars": 8000,
            "static_resends": 2,
            "reused_tool_calls": 1,
            "nested_rounds": 4,
        },
    }
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=True,
    )
    out = proc.stdout.strip()
    assert "ref_saved=12000" in out
    assert "fold_chars=8000" in out
    assert "static_resends=2" in out
    assert "reused_tools=1" in out
    assert "nested_rounds=4" in out


def test_each_and_session_summary_for_long_session() -> None:
    lines = [
        json.dumps(
            {
                "kind": "diagnostic",
                "data": {"rounds": 2, "request_input_tokens": 10000, "tool_calls": 1},
            }
        ),
        json.dumps({"kind": "section11_round_marker", "data": {"round": 1}}),
        json.dumps(
            {
                "kind": "diagnostic",
                "data": {
                    "rounds": 2,
                    "request_input_tokens": 12000,
                    "tool_calls": 1,
                    "referenced_chars_saved": 5000,
                },
            }
        ),
    ]
    text = "\n".join(lines)
    each = subprocess.run(
        [sys.executable, str(SCRIPT), "--each"],
        input=text,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "turn=1" in each.stdout
    assert "turn=2" in each.stdout
    assert "in=10000" in each.stdout
    assert "in=12000" in each.stdout
    summary = subprocess.run(
        [sys.executable, str(SCRIPT), "--session-summary"],
        input=text,
        capture_output=True,
        text=True,
        check=True,
    )
    out = summary.stdout.strip()
    assert "diagnostics=2" in out
    assert "in_first=10000" in out
    assert "in_last=12000" in out
    assert "in_last_over_first=1.20" in out
    assert "below_linear_2x=yes" in out


def test_one_liner_includes_provider_tool_count_when_present() -> None:
    line = json.dumps(
        {
            "kind": "diagnostic",
            "data": {"rounds": 1, "request_input_tokens": 100, "provider_tool_count": 3},
        }
    )
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--each"],
        input=line,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "provider_tools=3" in proc.stdout


def test_p0_baseline_table_from_events_dir(tmp_path: Path) -> None:
    events = tmp_path / "events"
    events.mkdir()
    (events / "01-no-tools.jsonl").write_text(
        json.dumps(
            {
                "kind": "diagnostic",
                "data": {
                    "rounds": 1,
                    "request_input_tokens": 10934,
                    "request_output_tokens": 117,
                    "tool_calls": 0,
                    "provider_tool_count": 11,
                    "components": {"final": 10271},
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (events / "01-probe.jsonl").write_text(
        json.dumps(
            {"kind": "diagnostic", "data": {"rounds": 1, "request_input_tokens": 0, "tool_calls": 0}}
        )
        + "\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--p0-baseline", str(events)],
        capture_output=True,
        text=True,
        check=True,
    )
    out = proc.stdout
    assert "10934" in out
    assert "01-no-tools.jsonl" in out
    assert "provider_tools=11" in out
    assert "comp_final=10271" in out
    assert "1 تحية" in out or "| 1 " in out


def test_session_summary_flags_quota_when_all_input_zero() -> None:
    lines = [
        json.dumps(
            {"kind": "diagnostic", "data": {"rounds": 1, "request_input_tokens": 0, "tool_calls": 0}}
        )
        for _ in range(5)
    ]
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--session-summary"],
        input="\n".join(lines),
        capture_output=True,
        text=True,
        check=True,
    )
    out = proc.stdout.strip()
    assert "diagnostics=5" in out
    assert "quota_blocked_likely=yes" in out


def test_resolve_row_prefers_highest_in_and_excludes_stem(tmp_path: Path) -> None:
    (tmp_path / "01-low.jsonl").write_text(
        json.dumps({"kind": "diagnostic", "data": {"rounds": 1, "input_tokens": 100}}) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "01-high.jsonl").write_text(
        json.dumps({"kind": "diagnostic", "data": {"rounds": 1, "input_tokens": 9000}}) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "01-no-tools-after-p0.jsonl").write_text(
        json.dumps({"kind": "diagnostic", "data": {"rounds": 1, "input_tokens": 5000}}) + "\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--resolve-row",
            "1",
            "--dir",
            str(tmp_path),
            "--exclude-stem",
            "after-p0",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert proc.stdout.strip().endswith("01-high.jsonl")


def test_pick_row_3_prefers_two_tools_over_higher_input_one_tool(tmp_path: Path) -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from mokli_upgrade_diagnostic_extract import pick_row_diagnostic

    (tmp_path / "03-multi-tool.jsonl").write_text(
        json.dumps(
            {
                "kind": "diagnostic",
                "data": {"rounds": 2, "input_tokens": 30000, "tool_calls": 1},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "03-multi-tool-v2.jsonl").write_text(
        json.dumps(
            {
                "kind": "diagnostic",
                "data": {"rounds": 3, "input_tokens": 28000, "tool_calls": 2},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    picked = pick_row_diagnostic(tmp_path, 3)
    assert picked is not None
    assert picked[0] == "03-multi-tool-v2.jsonl"


def test_pick_row_9_prefers_more_diagnostics_with_nonzero_input(tmp_path: Path) -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from mokli_upgrade_diagnostic_extract import pick_row_diagnostic

    def diag_line(in_t: int) -> str:
        return (
            json.dumps(
                {
                    "kind": "diagnostic",
                    "data": {"rounds": 1, "input_tokens": in_t, "tool_calls": 1},
                }
            )
            + "\n"
        )

    (tmp_path / "09-long-session-v2.jsonl").write_text(
        diag_line(5000) * 14 + diag_line(0),
        encoding="utf-8",
    )
    (tmp_path / "09-long-session-v3.jsonl").write_text(
        diag_line(4000) * 15,
        encoding="utf-8",
    )
    picked = pick_row_diagnostic(tmp_path, 9)
    assert picked is not None
    assert picked[0] == "09-long-session-v3.jsonl"


def test_jsonl_spawn_failed_upstream_quota_detects_spawn_429() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from mokli_upgrade_diagnostic_extract import jsonl_spawn_failed_upstream_quota

    body = (
        '{"kind":"tool","data":{"name":"spawn","event":"failed",'
        '"summary":"code": 429, rate-limited upstream"}}\n'
    )
    assert jsonl_spawn_failed_upstream_quota(body) is True
    assert jsonl_spawn_failed_upstream_quota('{"kind":"diagnostic","data":{}}\n') is False


def test_pick_row_5_prefers_nested_rounds(tmp_path: Path) -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from mokli_upgrade_diagnostic_extract import pick_row_diagnostic

    (tmp_path / "05-subagents.jsonl").write_text(
        json.dumps(
            {
                "kind": "diagnostic",
                "data": {"rounds": 4, "input_tokens": 50000, "tool_calls": 4, "nested_rounds": 0},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "05-subagents-v2.jsonl").write_text(
        json.dumps(
            {
                "kind": "diagnostic",
                "data": {"rounds": 3, "input_tokens": 40000, "tool_calls": 3, "nested_rounds": 2},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    picked = pick_row_diagnostic(tmp_path, 5)
    assert picked is not None
    assert picked[0] == "05-subagents-v2.jsonl"


def test_pick_row_3_prefers_v2_two_tools_over_v1_quota_fail(tmp_path: Path) -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from mokli_upgrade_diagnostic_extract import pick_row_diagnostic

    (tmp_path / "03-multi-tool.jsonl").write_text(
        json.dumps(
            {
                "kind": "diagnostic",
                "data": {"rounds": 2, "input_tokens": 0, "tool_calls": 1},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "03-multi-tool-v2.jsonl").write_text(
        json.dumps(
            {
                "kind": "diagnostic",
                "data": {"rounds": 3, "input_tokens": 26000, "tool_calls": 2},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    picked = pick_row_diagnostic(tmp_path, 3)
    assert picked is not None
    assert picked[0] == "03-multi-tool-v2.jsonl"


def test_pick_row_8_prefers_nonzero_input_over_quota_fail(tmp_path: Path) -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from mokli_upgrade_diagnostic_extract import pick_row_diagnostic

    (tmp_path / "08-fallback-provider.jsonl").write_text(
        json.dumps(
            {
                "kind": "diagnostic",
                "data": {"rounds": 1, "input_tokens": 0, "tool_calls": 0},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "08-fallback-provider-v2.jsonl").write_text(
        json.dumps(
            {
                "kind": "diagnostic",
                "data": {"rounds": 1, "input_tokens": 9000, "tool_calls": 0},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    picked = pick_row_diagnostic(tmp_path, 8)
    assert picked is not None
    assert picked[0] == "08-fallback-provider-v2.jsonl"
    assert picked[1]["input_tokens"] == 9000


def test_sample_fixture_jsonl_for_operator() -> None:
    fixture = ROOT / "tests/fixtures" / "section11_turn_diagnostics_sample.jsonl"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--file", str(fixture)],
        capture_output=True,
        text=True,
        check=True,
    )
    out = proc.stdout.strip()
    assert "rounds=1" in out
    assert "in=9500" in out
