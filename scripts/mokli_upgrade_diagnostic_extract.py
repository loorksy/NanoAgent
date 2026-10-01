#!/usr/bin/env python3
"""Extract the last turn diagnostic payload for Mokli upgrade verification (report §11).

Usage after a live chat turn with SHOW_DIAGNOSTICS enabled on the Mokli pipe:

  # From a saved JSONL log of gateway SSE events (one JSON object per line):
  python scripts/mokli_upgrade_diagnostic_extract.py --file /path/to/events.jsonl

  # From stdin:
  curl ... | python scripts/mokli_upgrade_diagnostic_extract.py

Each line may be either:
  - {"kind": "diagnostic", "data": {...}}
  - {"type": "diagnostic", "data": {...}}  (Open WebUI pipe internal)
  - the diagnostic dict itself (must contain "rounds" or "input_tokens")
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


def _diagnostic_from_obj(obj: dict[str, Any]) -> dict[str, Any] | None:
    kind = obj.get("kind") or obj.get("type")
    if kind == "diagnostic":
        data = obj.get("data")
        return data if isinstance(data, dict) else None
    if "request_input_tokens" in obj or ("rounds" in obj and "tool_calls" in obj):
        return obj
    return None


def _input_tokens(diag: dict[str, Any]) -> int:
    raw = diag.get("request_input_tokens", diag.get("input_tokens"))
    try:
        return int(raw or 0)
    except (TypeError, ValueError):
        return 0


def all_diagnostics_from_text(text: str) -> list[dict[str, Any]]:
    """Return every diagnostic payload in file order (§11 row 9 long session)."""
    found: list[dict[str, Any]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(":"):
            continue
        if line.startswith("data:"):
            line = line[5:].strip()
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        diag = _diagnostic_from_obj(obj)
        if diag is not None:
            found.append(diag)
    return found


def session_summary_line(diags: list[dict[str, Any]]) -> str:
    """Aggregate §11 row 9 metrics across many turns in one JSONL."""
    if not diags:
        return "diagnostics=0"
    ins = [_input_tokens(d) for d in diags]
    tools = [int(d.get("tool_calls") or 0) for d in diags]
    first = ins[0]
    last = ins[-1]
    peak = max(ins)
    parts = [
        f"diagnostics={len(diags)}",
        f"in_first={first}",
        f"in_last={last}",
        f"in_peak={peak}",
        f"tools_total={sum(tools)}",
    ]
    if first > 0:
        parts.append(f"in_last_over_first={last / first:.2f}")
        parts.append(f"in_peak_over_first={peak / first:.2f}")
        linear_15x = first * len(diags)
        parts.append(f"below_linear_{len(diags)}x={'yes' if peak < linear_15x else 'no'}")
    fold = sum(
        int(d.get("referenced_chars_saved") or 0)
        + int(d.get("folded_candle_chars") or 0)
        + int(d.get("folded_subagent_chars") or 0)
        for d in diags
    )
    if fold:
        parts.append(f"fold_saved_total={fold}")
    return " ".join(parts)


def _scan_lines(lines: list[str]) -> dict[str, Any] | None:
    last: dict[str, Any] | None = None
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith(":"):
            continue
        if line.startswith("data:"):
            line = line[5:].strip()
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        diag = _diagnostic_from_obj(obj)
        if diag is not None:
            last = diag
    return last


def diagnostic_from_text(text: str) -> dict[str, Any] | None:
    """Return the last diagnostic payload found in JSONL/SSE text."""
    return _scan_lines(text.splitlines())


def one_line_summary(diag: dict[str, Any]) -> str:
    """Format one §11 numbers column from a diagnostic dict."""
    return _one_line_summary(diag)


def _p0_fold_suffix(diag: dict[str, Any]) -> str:
    """Extra §11 numbers for long-session / P0 checks (omitted when all zero)."""
    extra: list[str] = []
    ref_saved = int(diag.get("referenced_chars_saved") or 0)
    if ref_saved:
        extra.append(f"ref_saved={ref_saved}")
    fold_chars = (
        int(diag.get("folded_reasoning_chars") or 0)
        + int(diag.get("folded_candle_chars") or 0)
        + int(diag.get("folded_subagent_chars") or 0)
    )
    if fold_chars:
        extra.append(f"fold_chars={fold_chars}")
    static_resends = int(diag.get("static_resends") or 0)
    if static_resends:
        extra.append(f"static_resends={static_resends}")
    reused = int(diag.get("reused_tool_calls") or 0)
    if reused:
        extra.append(f"reused_tools={reused}")
    nested_rounds = int(diag.get("nested_rounds") or 0)
    if nested_rounds:
        extra.append(f"nested_rounds={nested_rounds}")
    if not extra:
        return ""
    return " " + " ".join(extra)


def _one_line_summary(diag: dict[str, Any]) -> str:
    parts = [
        f"rounds={diag.get('rounds')}",
        f"in={diag.get('request_input_tokens', diag.get('input_tokens'))}",
        f"out={diag.get('request_output_tokens', diag.get('output_tokens'))}",
        f"tools={diag.get('tool_calls')}",
        f"ctx_ms={diag.get('context_ms')}",
        f"model_ms={diag.get('model_ms')}",
        f"tool_ms={diag.get('tool_ms')}",
        f"retry_ms={diag.get('retry_ms')}",
        f"nested_in={diag.get('nested_input_tokens')}",
    ]
    base = " ".join(str(p) for p in parts if not str(p).endswith("=None"))
    return base + _p0_fold_suffix(diag)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=str, help="JSONL file of gateway or pipe events")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print full diagnostic JSON instead of a one-line §11 summary",
    )
    parser.add_argument(
        "--each",
        action="store_true",
        help="Print one summary line per diagnostic (long session / row 9)",
    )
    parser.add_argument(
        "--session-summary",
        action="store_true",
        help="Print aggregate input-token growth across all diagnostics (row 9)",
    )
    args = parser.parse_args()
    if args.file:
        text = open(args.file, encoding="utf-8").read()
    else:
        text = sys.stdin.read()
    if args.session_summary:
        diags = all_diagnostics_from_text(text)
        if not diags:
            print("No diagnostic event found.", file=sys.stderr)
            return 1
        print(session_summary_line(diags))
        return 0
    if args.each:
        diags = all_diagnostics_from_text(text)
        if not diags:
            print("No diagnostic event found.", file=sys.stderr)
            return 1
        for idx, diag in enumerate(diags, start=1):
            print(f"turn={idx} " + one_line_summary(diag))
        return 0
    diag = diagnostic_from_text(text)
    if diag is None:
        print("No diagnostic event found.", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(diag, ensure_ascii=False, indent=2))
    else:
        print(one_line_summary(diag))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
