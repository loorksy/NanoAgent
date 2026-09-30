#!/usr/bin/env python3
"""Batch §11 numbers from multiple saved JSONL event logs (operator handoff).

Each file should be one live scenario (rows 1–13 in report §11). Name files with a
numeric prefix for ordering, e.g. ``01-greeting.jsonl``, ``04-gold-buy.jsonl``.

  python scripts/mokli_upgrade_section11_batch.py --dir ./section11-events/
  python scripts/mokli_upgrade_section11_batch.py --dir ./section11-events/ --markdown
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

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
    args = parser.parse_args()
    directory = args.dir.expanduser().resolve()
    if not directory.is_dir():
        print(f"Not a directory: {directory}", file=sys.stderr)
        return 1

    files = _collect_jsonl(directory)
    if not files:
        print(f"No *.jsonl in {directory}", file=sys.stderr)
        return 1

    rows: list[tuple[int | str, str, str]] = []
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
        rows.append((label, path.name, numbers))

    if args.markdown:
        print("| # | ملف JSONL | أرقام (paste into §11) |")
        print("| --- | --- | --- |")
        for label, fname, numbers in rows:
            print(f"| {label} | `{fname}` | {numbers} |")
    else:
        for label, fname, numbers in rows:
            print(f"{label}\t{fname}\t{numbers}")

    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
