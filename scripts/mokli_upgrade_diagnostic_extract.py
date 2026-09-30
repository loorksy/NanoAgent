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
    return " ".join(str(p) for p in parts if not str(p).endswith("=None"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=str, help="JSONL file of gateway or pipe events")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print full diagnostic JSON instead of a one-line §11 summary",
    )
    args = parser.parse_args()
    if args.file:
        text = open(args.file, encoding="utf-8").read()
    else:
        text = sys.stdin.read()
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
