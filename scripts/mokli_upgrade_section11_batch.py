#!/usr/bin/env python3
"""Batch §11 numbers from multiple saved JSONL event logs (operator handoff).

Each file should be one live scenario (rows 1–13 in report §11). Name files with a
numeric prefix for ordering, e.g. ``01-greeting.jsonl``, ``04-gold-buy.jsonl``.

  python scripts/mokli_upgrade_section11_batch.py --dir ./section11-events/
  python scripts/mokli_upgrade_section11_batch.py --dir ./section11-events/ --markdown
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Import helpers from sibling script (same directory on PYTHONPATH when invoked as file).
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from mokli_upgrade_diagnostic_extract import (  # noqa: E402
    all_diagnostics_from_text,
    one_line_summary,
    pick_row_diagnostic,
    session_summary_line,
)


def _row_index(name: str) -> int | None:
    prefix = name.split("-", 1)[0]
    if prefix.isdigit():
        return int(prefix)
    return None


def _collect_jsonl(directory: Path) -> list[Path]:
    files = sorted(directory.glob("*.jsonl"))
    return sorted(files, key=lambda p: (_row_index(p.stem) is None, _row_index(p.stem) or 0, p.name))


def _scenario_jsonl(directory: Path) -> list[Path]:
    """§11 scenario logs only (``01-….jsonl`` … ``13-….jsonl``), not quota probes."""
    return [p for p in _collect_jsonl(directory) if _row_index(p.stem) is not None]


def gather_section11_rows(
    directory: Path,
    results_path: Path | None = None,
) -> tuple[dict[int, tuple[str, str]], int]:
    """Build ``{row_id: (result_text, numbers_line)}`` from JSONL + optional results JSON."""
    results_map: dict[int, str] = {}
    if results_path is not None:
        results_map = _load_results(results_path)
    row_ids: set[int] = set()
    for path in _scenario_jsonl(directory):
        idx = _row_index(path.stem)
        if idx is not None:
            row_ids.add(idx)
    row_ids |= set(results_map.keys())
    out: dict[int, tuple[str, str]] = {}
    missing = 0
    for idx in sorted(row_ids):
        picked = pick_row_diagnostic(directory, idx)
        if picked is None:
            numbers = "(no diagnostic)"
            missing += 1
        else:
            name, diag = picked
            numbers = one_line_summary(diag)
            if idx == 9:
                path = directory / name
                diags = all_diagnostics_from_text(path.read_text(encoding="utf-8"))
                if len(diags) > 1:
                    numbers = f"{numbers} {session_summary_line(diags)}"
        result_text = results_map.get(idx, "")
        out[idx] = (result_text, numbers)
    return out, missing


def _load_results(path: Path) -> dict[int, str]:
    """Map §11 row number → operator «النتيجة» text (JSON object keys are row ids)."""
    raw: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("results file must be a JSON object")
    out: dict[int, str] = {}
    for key, value in raw.items():
        row_id = int(key)
        if isinstance(value, str):
            out[row_id] = value
        elif isinstance(value, dict) and isinstance(value.get("result"), str):
            out[row_id] = value["result"]
        else:
            raise ValueError(f"results[{key!r}] must be a string or {{\"result\": \"...\"}}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dir",
        type=Path,
        required=True,
        help="Directory of per-scenario JSONL logs (SHOW_DIAGNOSTICS saves)",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Print markdown table rows (§11 numbers column only)",
    )
    parser.add_argument(
        "--results",
        type=Path,
        help="JSON file: row id → «النتيجة» string (see docs/section11-results.example.json)",
    )
    args = parser.parse_args()
    directory = args.dir.expanduser().resolve()
    if not directory.is_dir():
        print(f"Not a directory: {directory}", file=sys.stderr)
        return 1

    scenario_files = _scenario_jsonl(directory)
    if not scenario_files:
        print(
            f"No §11 scenario *.jsonl (NN-prefix) in {directory}",
            file=sys.stderr,
        )
        return 1

    results_path: Path | None = None
    if args.results:
        results_path = args.results.expanduser().resolve()
        if not results_path.is_file():
            print(f"Results file not found: {results_path}", file=sys.stderr)
            return 1

    try:
        row_map, missing = gather_section11_rows(directory, results_path)
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"Invalid results file: {exc}", file=sys.stderr)
        return 1

    rows: list[tuple[int | str, str, str, str]] = []
    for path in scenario_files:
        idx = _row_index(path.stem)
        assert idx is not None
        label = str(idx)
        if idx in row_map:
            result_text, numbers = row_map[idx]
        else:
            result_text, numbers = "", "(no diagnostic)"
        rows.append((label, path.name, numbers, result_text))

    if args.markdown:
        if args.results:
            print("| # | النتيجة | أرقام | ملف JSONL |")
            print("| --- | --- | --- | --- |")
            for idx in sorted(row_map.keys()):
                result_text, numbers = row_map[idx]
                picked = pick_row_diagnostic(directory, idx)
                fname = picked[0] if picked is not None else "?"
                print(f"| {idx} | {result_text} | {numbers} | `{fname}` |")
        else:
            print("| # | ملف JSONL | أرقام (paste into §11) |")
            print("| --- | --- | --- |")
            for label, fname, numbers, _result in rows:
                print(f"| {label} | `{fname}` | {numbers} |")
    else:
        for label, fname, numbers, result_text in rows:
            if args.results:
                print(f"{label}\t{result_text}\t{numbers}\t{fname}")
            else:
                print(f"{label}\t{fname}\t{numbers}")

    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
