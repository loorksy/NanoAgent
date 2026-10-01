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
from pathlib import Path
from typing import Any

# Report §2.1 live snapshot rows (Agent API on VPS).
_P0_BASELINE_ROWS: dict[int, str] = {
    1: "تحية",
    2: "أداة واحدة",
    4: "تحليل/قرار",
    10: "backtest",
}


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
    elif len(diags) > 1 and peak == 0:
        parts.append("quota_blocked_likely=yes")
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


def _row_index_from_stem(stem: str) -> int | None:
    prefix = stem.split("-", 1)[0]
    if prefix.isdigit():
        return int(prefix)
    return None


def _row_pick_rank(row: int, diag: dict[str, Any]) -> tuple[Any, ...]:
    """Sort key for §11 row JSONL (higher is better). Quality before raw input size."""
    tin = _input_tokens(diag)
    tool_calls = int(diag.get("tool_calls") or 0)
    nested = int(diag.get("nested_rounds") or 0)
    if row == 3:
        return (1 if tool_calls >= 2 else 0, tool_calls, tin)
    if row == 5:
        return (1 if nested >= 1 else 0, nested, tin)
    if row == 8:
        return (1 if tin > 0 else 0, tin)
    return (tin,)


def _row9_pick_rank(diags: list[dict[str, Any]]) -> tuple[Any, ...]:
    ins = [_input_tokens(d) for d in diags]
    peak = max(ins) if ins else 0
    last = ins[-1] if ins else 0
    quota_tail = last == 0 and peak > 0 and len(diags) > 1
    return (1 if peak > 0 else 0, len(diags), 0 if quota_tail else 1, peak)


def _best_diagnostic_for_row(row: int, text: str) -> dict[str, Any] | None:
    if row == 9:
        diags = all_diagnostics_from_text(text)
        if not diags:
            return None
        for diag in reversed(diags):
            if _input_tokens(diag) > 0:
                return diag
        return diags[-1]
    return diagnostic_from_text(text)


def pick_row_diagnostic(
    directory: Path,
    row: int,
    *,
    exclude_stem_substrings: tuple[str, ...] = (),
) -> tuple[str, dict[str, Any]] | None:
    """Best diagnostic for a §11 row (row-aware quality, then input_tokens)."""
    best_name = ""
    best_diag: dict[str, Any] | None = None
    best_rank: tuple[Any, ...] = ()
    for path in sorted(directory.glob("*.jsonl")):
        if _row_index_from_stem(path.stem) != row:
            continue
        if exclude_stem_substrings and any(s in path.stem for s in exclude_stem_substrings):
            continue
        text = path.read_text(encoding="utf-8")
        if row == 9:
            diags = all_diagnostics_from_text(text)
            if not diags:
                continue
            rank = _row9_pick_rank(diags)
            diag = _best_diagnostic_for_row(9, text)
        else:
            diag = diagnostic_from_text(text)
            if diag is None:
                continue
            rank = _row_pick_rank(row, diag)
        if rank > best_rank:
            best_rank = rank
            best_diag = diag
            best_name = path.name
    if best_diag is None:
        return None
    return best_name, best_diag


def resolve_row_jsonl(
    directory: Path,
    row: int,
    *,
    prefer_name: str | None = None,
    exclude_stem_substrings: tuple[str, ...] = (),
) -> Path | None:
    """Path to the canonical JSONL for a §11 row (see ``pick_row_diagnostic``)."""
    if prefer_name:
        preferred = directory / prefer_name
        if preferred.is_file() and diagnostic_from_text(preferred.read_text(encoding="utf-8")):
            return preferred
    picked = pick_row_diagnostic(
        directory,
        row,
        exclude_stem_substrings=exclude_stem_substrings,
    )
    if picked is None:
        return None
    return directory / picked[0]


def p0_baseline_markdown(directory: Path) -> str:
    """Markdown table rows for report §2.1 from on-disk §11 JSONL."""
    lines = [
        "| مسار §11 | `in` | `out` | `tools` | `rounds` | ملاحظة |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row_id, label in sorted(_P0_BASELINE_ROWS.items()):
        picked = pick_row_diagnostic(directory, row_id)
        if picked is None:
            lines.append(f"| {row_id} {label} | — | — | — | — | no JSONL/diagnostic |")
            continue
        name, diag = picked
        note = f"`{name}`"
        if _input_tokens(diag) == 0:
            note += "; quota_blocked?"
        provider_tools = diag.get("provider_tool_count")
        if provider_tools is not None and int(provider_tools or 0) > 0:
            note += f"; provider_tools={int(provider_tools)}"
        comp = diag.get("components") or {}
        final = comp.get("final")
        if isinstance(final, int) and final > 0:
            note += f"; comp_final={final}"
        lines.append(
            "| {label} | {in_t} | {out_t} | {tools} | {rounds} | {note} |".format(
                label=f"{row_id} {label}",
                in_t=_input_tokens(diag),
                out_t=int(diag.get("request_output_tokens") or diag.get("output_tokens") or 0),
                tools=int(diag.get("tool_calls") or 0),
                rounds=int(diag.get("rounds") or 0),
                note=note,
            )
        )
    return "\n".join(lines)


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
    provider_tools = diag.get("provider_tool_count")
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
    suffix = _p0_fold_suffix(diag)
    if provider_tools is not None and int(provider_tools or 0) > 0:
        suffix += f" provider_tools={int(provider_tools)}"
    return base + suffix


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
    parser.add_argument(
        "--p0-baseline",
        type=Path,
        metavar="DIR",
        help="Print markdown table for report §2.1 from section11-events JSONL",
    )
    parser.add_argument(
        "--resolve-row",
        type=int,
        metavar="N",
        help="Print path to best JSONL for §11 row N (with --dir)",
    )
    parser.add_argument(
        "--dir",
        type=Path,
        metavar="DIR",
        help="Events directory (for --resolve-row)",
    )
    parser.add_argument(
        "--prefer",
        type=str,
        help="Prefer this filename when resolving a row JSONL",
    )
    parser.add_argument(
        "--exclude-stem",
        action="append",
        default=[],
        help="Skip JSONL stems containing this substring (repeatable)",
    )
    args = parser.parse_args()
    if args.resolve_row is not None:
        if args.dir is None:
            print("--resolve-row requires --dir", file=sys.stderr)
            return 2
        directory = args.dir.expanduser().resolve()
        if not directory.is_dir():
            print(f"Not a directory: {directory}", file=sys.stderr)
            return 1
        path = resolve_row_jsonl(
            directory,
            args.resolve_row,
            prefer_name=args.prefer,
            exclude_stem_substrings=tuple(args.exclude_stem or ()),
        )
        if path is None:
            return 1
        print(path)
        return 0
    if args.p0_baseline is not None:
        directory = args.p0_baseline.expanduser().resolve()
        if not directory.is_dir():
            print(f"Not a directory: {directory}", file=sys.stderr)
            return 1
        print(p0_baseline_markdown(directory))
        return 0
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
