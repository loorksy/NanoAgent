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

from mokli_upgrade_diagnostic_extract import diagnostic_from_text, one_line_summary  # noqa: E402


def _row_index(name: str) -> int | None:
    prefix = name.split("-", 1)[0]
    if prefix.isdigit():
        return int(prefix)
    return None


def _collect_jsonl(directory: Path) -> list[Path]:
    files = sorted(directory.glob("*.jsonl"))
    return sorted(files, key=lambda p: (_row_index(p.stem) is None, _row_index(p.stem) or 0, p.name))


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

    files = _collect_jsonl(directory)
    if not files:
        print(f"No *.jsonl in {directory}", file=sys.stderr)
        return 1

    results_map: dict[int, str] = {}
    if args.results:
        results_path = args.results.expanduser().resolve()
        if not results_path.is_file():
            print(f"Results file not found: {results_path}", file=sys.stderr)
            return 1
        try:
            results_map = _load_results(results_path)
        except (json.JSONDecodeError, ValueError) as exc:
            print(f"Invalid results file: {exc}", file=sys.stderr)
            return 1

    rows: list[tuple[int | str, str, str, str]] = []
    missing = 0
    for path in files:
        idx = _row_index(path.stem)
        label = str(idx) if idx is not None else path.stem
        text = path.read_text(encoding="utf-8")
        diag = diagnostic_from_text(text)
        if diag is None:
            numbers = "(no diagnostic)"
            missing += 1
        else:
            numbers = one_line_summary(diag)
        result_text = ""
        if idx is not None:
            result_text = results_map.get(idx, "")
        rows.append((label, path.name, numbers, result_text))

    if args.markdown:
        if args.results:
            print("| # | النتيجة | أرقام | ملف JSONL |")
            print("| --- | --- | --- | --- |")
            for label, fname, numbers, result_text in rows:
                print(f"| {label} | {result_text} | {numbers} | `{fname}` |")
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
