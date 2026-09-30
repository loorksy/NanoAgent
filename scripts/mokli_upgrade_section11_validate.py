#!/usr/bin/env python3
"""Validate operator artifacts before pasting into report §11.

Checks (does not call LLM or broker):
  - ``section11-events/*.jsonl`` named with numeric prefix 01–13 (or 14)
  - each file contains at least one diagnostic event
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

from mokli_upgrade_diagnostic_extract import diagnostic_from_text  # noqa: E402
from mokli_upgrade_section11_batch import _load_results, _row_index  # noqa: E402


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
    for path in directory.glob("*.jsonl"):
        idx = _row_index(path.stem)
        if idx is None:
            continue
        found_rows.add(idx)
        if diagnostic_from_text(path.read_text(encoding="utf-8")) is None:
            errors.append(f"No diagnostic in {path.name}")

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

    if errors:
        for msg in errors:
            print(f"ERROR {msg}", file=sys.stderr)
        return 1

    print(
        f"OK §11 artifacts: rows 1–{args.require_through} have JSONL+diagnostic and non-empty results"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
