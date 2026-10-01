#!/usr/bin/env python3
"""Validate operator artifacts before pasting into report §11.

Checks (does not call LLM or broker):
  - ``section11-events/*.jsonl`` named with numeric prefix 01–13 (or 14)
  - each required row has at least one scenario JSONL with a diagnostic (``NN-*.jsonl``)
  - ``section11-results.json`` has non-empty «النتيجة» for required rows

  python scripts/mokli_upgrade_section11_validate.py \\
    --dir ./section11-events --results section11-results.json --require-through 13
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from mokli_upgrade_diagnostic_extract import (  # noqa: E402
    all_diagnostics_from_text,
    diagnostic_from_text,
    pick_row_diagnostic,
    session_summary_line,
)
from mokli_upgrade_section11_batch import _load_results, _row_index, _scenario_jsonl  # noqa: E402


def _closure_hints(empty_result: list[int]) -> None:
    missing_ui = sorted(r for r in empty_result if r in (11, 12, 13))
    if missing_ui:
        print(
            f"HINT rows {missing_ui}: empty «النتيجة» — "
            "bash scripts/mokli_upgrade_section11_remaining_rows.sh",
            file=sys.stderr,
        )
    if 11 in empty_result:
        print(
            "HINT row 11 JSONL: 11-paper.jsonl (vps_section11_row11_paper.sh; needs OANDA)",
            file=sys.stderr,
        )
    if 12 in empty_result:
        print(
            "HINT row 12 JSONL: 12-desktop-ui.jsonl (Mokli UI pipe + SHOW_DIAGNOSTICS)",
            file=sys.stderr,
        )
    if 13 in empty_result:
        print(
            "HINT row 13 CI proxy (no device/LLM): "
            "bash scripts/mokli_upgrade_section11_row13_ci.sh",
            file=sys.stderr,
        )
        print(
            "HINT row 13 production JSONL: 13-mobile.jsonl (device/SDK session)",
            file=sys.stderr,
        )


def _input_tokens(diag: dict) -> int:
    for key in ("request_input_tokens", "input_tokens"):
        val = diag.get(key)
        if isinstance(val, int):
            return val
        if isinstance(val, str) and val.isdigit():
            return int(val)
    return 0


def _quality_hints(directory: Path, require_through: int) -> None:
    if require_through >= 1 and not (directory / "01-no-tools-after-p0.jsonl").is_file():
        picked = pick_row_diagnostic(directory, 1)
        if picked is not None:
            name, diag = picked
            tin = _input_tokens(diag)
            if tin > 8000:
                print(
                    f"HINT row 1 P0 ({name}): baseline in={tin}, no after-p0 JSONL — "
                    "bash scripts/vps_section11_row1_after_p0.sh",
                    file=sys.stderr,
                )
    if require_through >= 3:
        picked = pick_row_diagnostic(directory, 3)
        if picked is not None:
            name, diag = picked
            tool_calls = int(diag.get("tool_calls") or 0)
            if tool_calls < 2:
                print(
                    f"HINT row 3 ({name}): tool_calls={tool_calls} — "
                    "rerun bash scripts/vps_section11_row3_multi_tool.sh "
                    "(writes 03-multi-tool-v2.jsonl)",
                    file=sys.stderr,
                )
    if require_through >= 5:
        picked = pick_row_diagnostic(directory, 5)
        if picked is not None:
            name, diag = picked
            nested = int(diag.get("nested_rounds") or 0)
            if nested < 1:
                body = (directory / name).read_text(encoding="utf-8")
                if "spawn" in body and ("429" in body or "rate-limit" in body.lower()):
                    print(
                        f"HINT row 5 ({name}): spawn nested_rounds=0 (quota?) — "
                        "rerun bash scripts/vps_section11_row5_subagents.sh "
                        "(writes 05-subagents-v2.jsonl)",
                        file=sys.stderr,
                    )
    if require_through >= 9:
        picked = pick_row_diagnostic(directory, 9)
        if picked is not None:
            name, _diag = picked
            path = directory / name
            diags = all_diagnostics_from_text(path.read_text(encoding="utf-8"))
            if diags:
                summary = session_summary_line(diags)
                if "quota_blocked_likely=yes" in summary or (
                    "in_last=0" in summary and len(diags) > 1
                ):
                    print(
                        f"HINT row 9 ({name}): {summary} — "
                        "rerun bash scripts/vps_section11_row9_long_session.sh "
                        "(writes 09-long-session-v3.jsonl)",
                        file=sys.stderr,
                    )
    if require_through >= 10:
        picked = pick_row_diagnostic(directory, 10)
        if picked is not None:
            name, _diag = picked
            body = (directory / name).read_text(encoding="utf-8")
            if "market_feed_unconfigured" in body or "OANDA not configured" in body:
                print(
                    f"HINT row 10 ({name}): market feed unconfigured — "
                    "set OANDA_* then bash scripts/vps_section11_row10_backtest.sh",
                    file=sys.stderr,
                )


def _print_row_progress(
    directory: Path,
    results_map: dict[int, str],
    required: set[int],
) -> None:
    jsonl_name: dict[int, str] = {}
    has_diagnostic: dict[int, bool] = {}
    row_ids = {
        idx
        for p in _scenario_jsonl(directory)
        if (idx := _row_index(p.stem)) is not None
    }
    for row_id in sorted(row_ids):
        picked = pick_row_diagnostic(directory, row_id)
        if picked is not None:
            jsonl_name[row_id], diag = picked
            has_diagnostic[row_id] = bool(diag)
        else:
            has_diagnostic[row_id] = False

    print(f"§11 progress (rows {min(required)}–{max(required)}):", file=sys.stderr)
    for row_id in sorted(required):
        issues: list[str] = []
        if row_id not in jsonl_name:
            issues.append("no JSONL")
        elif not has_diagnostic.get(row_id):
            issues.append("no diagnostic in JSONL")
        text = results_map.get(row_id, "")
        if not str(text).strip():
            issues.append("empty «النتيجة»")
        elif "dry-run" in str(text).lower():
            issues.append("DRY-RUN placeholder")
        if issues:
            print(f"  {row_id:2d}: incomplete — {', '.join(issues)}", file=sys.stderr)
        else:
            print(f"  {row_id:2d}: ready", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, required=True, help="Directory of JSONL logs")
    parser.add_argument("--results", type=Path, required=True, help="Operator results JSON")
    parser.add_argument(
        "--require-through",
        type=int,
        default=13,
        help="Require rows 1..N (default 13; use 14 for optional MT5)",
    )
    args = parser.parse_args()
    directory = args.dir.expanduser().resolve()
    results_path = args.results.expanduser().resolve()
    required = set(range(1, args.require_through + 1))

    errors: list[str] = []
    if not directory.is_dir():
        errors.append(f"Missing events dir: {directory}")
    if not results_path.is_file():
        errors.append(f"Missing results file: {results_path}")

    if errors:
        for msg in errors:
            print(f"ERROR {msg}", file=sys.stderr)
        return 1

    try:
        results_map = _load_results(results_path)
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR invalid results: {exc}", file=sys.stderr)
        return 1

    found_rows: set[int] = set()
    for path in _scenario_jsonl(directory):
        idx = _row_index(path.stem)
        if idx is not None:
            found_rows.add(idx)
    for row_id in sorted(required & found_rows):
        if pick_row_diagnostic(directory, row_id) is None:
            errors.append(f"No diagnostic for §11 row {row_id}")

    missing_jsonl = sorted(required - found_rows)
    if missing_jsonl:
        errors.append(f"Missing JSONL for rows: {missing_jsonl}")

    missing_result: list[int] = []
    empty_result: list[int] = []
    for row_id in sorted(required):
        text = results_map.get(row_id)
        if text is None:
            missing_result.append(row_id)
        elif not str(text).strip():
            empty_result.append(row_id)

    if missing_result:
        errors.append(f"Results JSON missing keys: {missing_result}")
    if empty_result:
        errors.append(f"Empty «النتيجة» for rows: {empty_result}")

    dry_run_rows: list[int] = []
    for row_id in sorted(required):
        text = results_map.get(row_id)
        if text and "dry-run" in str(text).lower():
            dry_run_rows.append(row_id)
    if dry_run_rows and (
        args.require_through > 1 or dry_run_rows != [1]
    ):
        errors.append(
            f"Placeholder DRY-RUN in results for rows {dry_run_rows} — "
            "replace with live §11 text before production validate"
        )

    if errors:
        _print_row_progress(directory, results_map, required)
        _quality_hints(directory, min(args.require_through, 10))
        _closure_hints(empty_result)
        for msg in errors:
            print(f"ERROR {msg}", file=sys.stderr)
        return 1

    print(
        f"OK §11 artifacts: rows 1–{args.require_through} have JSONL+diagnostic and non-empty results"
    )
    _quality_hints(directory, args.require_through)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
