#!/usr/bin/env python3
"""Patch §11 «النتيجة»/«الأرقام» columns in docs/mokli-agent-upgrade-report.md.

Run only after live scenarios and ``section11_validate`` (production rows).

  python scripts/mokli_upgrade_section11_patch_report.py \\
    --dir ./section11-events --results section11-results.json \\
    --report docs/mokli-agent-upgrade-report.md --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from mokli_upgrade_section11_batch import gather_section11_rows  # noqa: E402
from mokli_upgrade_diagnostic_extract import (  # noqa: E402
    pick_row_diagnostic,
    p0_baseline_markdown,
)

_ROW_LINE = re.compile(r"^\|\s*(\d+)\s*\|")
_P0_TABLE_HEADER = "| مسار §11 | `in` | `out` | `tools` | `rounds` | ملاحظة |"
_P0_INTERIM_LINE = re.compile(r"^\*\*P0 مكونات \(VPS.*$", re.MULTILINE)
_P0_LIVE_DELTA_LINE = re.compile(r"^\*\*P0 live delta \(VPS.*$", re.MULTILINE)
_PENDING_HEADER = "(لم تُنفَّذ في Cloud Agent)"
_FILLED_HEADER = "(تم التعبئة من تشغيل VPS — راجع الأرقام واللقطات)"
# Report markdown may use a different combining-mark order for «نُفِّذ»; match by section title.
_PENDING_SECTION_HEADER_RE = re.compile(
    r"(##\s*11\.\s*مسارات حية\s*)\([^)]*Cloud\s+Agent[^)]*\)",
    re.UNICODE,
)


def _patch_table_line(line: str, payloads: dict[int, tuple[str, str]]) -> str:
    match = _ROW_LINE.match(line)
    if not match:
        return line
    row_id = int(match.group(1))
    if row_id not in payloads:
        return line
    result_text, numbers = payloads[row_id]
    if not result_text.strip() and not numbers.strip():
        return line
    if "|" in result_text or "|" in numbers:
        raise ValueError(f"Row {row_id}: «النتيجة»/«الأرقام» must not contain '|'")
    parts = line.split("|")
    if len(parts) < 7:
        return line
    parts[5] = f" {result_text.strip()} "
    parts[6] = f" {numbers.strip()} "
    return "|".join(parts)


def patch_report_text(text: str, payloads: dict[int, tuple[str, str]]) -> tuple[str, int]:
    changed = 0
    out_lines: list[str] = []
    for line in text.splitlines():
        new_line = _patch_table_line(line, payloads)
        if new_line != line:
            changed += 1
        out_lines.append(new_line)
    return "\n".join(out_lines) + ("\n" if text.endswith("\n") else ""), changed


def _maybe_update_section_header(
    text: str,
    payloads: dict[int, tuple[str, str]],
    require_through: int,
) -> tuple[str, bool]:
    required = set(range(1, require_through + 1))
    if not required.issubset(payloads.keys()):
        return text, False
    for row_id in sorted(required):
        result_text, numbers = payloads[row_id]
        if not str(result_text).strip() or not str(numbers).strip():
            return text, False
        if "dry-run" in str(result_text).lower():
            return text, False
    if _FILLED_HEADER in text and not _PENDING_SECTION_HEADER_RE.search(text):
        return text, False
    match = _PENDING_SECTION_HEADER_RE.search(text)
    if match:
        updated = _PENDING_SECTION_HEADER_RE.sub(rf"\1{_FILLED_HEADER}", text, count=1)
        return updated, updated != text
    if _PENDING_HEADER in text:
        return text.replace(_PENDING_HEADER, _FILLED_HEADER, 1), True
    return text, False


def patch_p0_baseline_table(text: str, events_dir: Path) -> tuple[str, int]:
    """Replace report §2.1 snapshot table from section11-events diagnostics."""
    lines = text.splitlines()
    start: int | None = None
    end: int | None = None
    for idx, line in enumerate(lines):
        if line.strip() == _P0_TABLE_HEADER:
            start = idx
            continue
        if start is not None and line.startswith("**"):
            end = idx
            break
    if start is None:
        return text, 0
    if end is None:
        end = len(lines)
    new_block = p0_baseline_markdown(events_dir).splitlines()
    if end < len(lines) and lines[end].startswith("**"):
        if new_block and new_block[-1].strip():
            new_block.append("")
    if lines[start:end] == new_block:
        return text, 0
    updated_lines = lines[:start] + new_block + lines[end:]
    updated = "\n".join(updated_lines)
    if text.endswith("\n"):
        updated += "\n"
    return updated, 1


def _parse_p0_live_delta_stdout(stdout: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in stdout.splitlines():
        if line.startswith("delta_in="):
            parsed["delta_in"] = line.partition("=")[2]
        elif line.startswith("delta_comp_final="):
            parsed["delta_comp_final"] = line.partition("=")[2]
        elif line.startswith("baseline="):
            for token in line.split():
                if token.startswith("in="):
                    parsed["base_in"] = token[3:]
        elif line.startswith("new="):
            for token in line.split():
                if token.startswith("in="):
                    parsed["new_in"] = token[3:]
    return parsed


def patch_p0_live_delta_paragraph(text: str, events_dir: Path) -> tuple[str, int]:
    """When after-p0 JSONL has in>0, replace interim §2.1 P0 components bullet."""
    after = events_dir / "01-no-tools-after-p0.jsonl"
    if not after.is_file():
        return text, 0
    baseline = events_dir / "01-no-tools.jsonl"
    if not baseline.is_file():
        picked = pick_row_diagnostic(events_dir, 1, exclude_stem_substrings=["after-p0"])
        if picked is None:
            return text, 0
        baseline = events_dir / picked[0]
    script = _SCRIPT_DIR / "mokli_upgrade_p0_live_delta.sh"
    proc = subprocess.run(
        ["bash", str(script), str(baseline), str(after)],
        capture_output=True,
        text=True,
        check=False,
        cwd=_SCRIPT_DIR.parent,
    )
    if proc.returncode != 0:
        return text, 0
    metrics = _parse_p0_live_delta_stdout(proc.stdout)
    new_in = metrics.get("new_in")
    if not new_in or not new_in.isdigit() or int(new_in) <= 0:
        return text, 0
    base_in = metrics.get("base_in", "?")
    delta_in = metrics.get("delta_in", "?")
    comp_note = ""
    if metrics.get("delta_comp_final"):
        comp_note = f"; `delta_comp_final={metrics['delta_comp_final']}`"
    new_line = (
        "**P0 live delta (VPS row 1 — `01-no-tools-after-p0.jsonl`):** "
        f"baseline `in={base_in}` → after `in={new_in}` (`delta_in={delta_in}`{comp_note})."
    )
    if _P0_LIVE_DELTA_LINE.search(text):
        updated, count = _P0_LIVE_DELTA_LINE.subn(new_line, text, count=1)
        return updated, count
    if _P0_INTERIM_LINE.search(text):
        updated, count = _P0_INTERIM_LINE.subn(new_line, text, count=1)
        return updated, count
    return text, 0


def apply_section11_patch(
    text: str,
    payloads: dict[int, tuple[str, str]],
    *,
    require_through: int = 13,
    events_dir: Path | None = None,
) -> tuple[str, int]:
    updated, changed = patch_report_text(text, payloads)
    updated, header_changed = _maybe_update_section_header(updated, payloads, require_through)
    if header_changed:
        changed += 1
    if events_dir is not None:
        updated, p0_changed = patch_p0_baseline_table(updated, events_dir)
        changed += p0_changed
        updated, live_changed = patch_p0_live_delta_paragraph(updated, events_dir)
        changed += live_changed
    return updated, changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, required=True, help="section11-events JSONL directory")
    parser.add_argument("--results", type=Path, required=True, help="section11-results.json")
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("docs/mokli-agent-upgrade-report.md"),
        help="Report markdown to patch (default: docs/mokli-agent-upgrade-report.md)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print changed row count only")
    parser.add_argument(
        "--skip-validate",
        action="store_true",
        help="Do not run section11_validate before patching",
    )
    parser.add_argument(
        "--require-through",
        type=int,
        default=13,
        help="Rows required when running validate (default 13)",
    )
    args = parser.parse_args()

    events_dir = args.dir.expanduser().resolve()
    results_path = args.results.expanduser().resolve()
    report_path = args.report.expanduser().resolve()

    if not report_path.is_file():
        print(f"Report not found: {report_path}", file=sys.stderr)
        return 1

    if not args.skip_validate:
        validate_script = _SCRIPT_DIR / "mokli_upgrade_section11_validate.py"
        proc = subprocess.run(
            [
                sys.executable,
                str(validate_script),
                "--dir",
                str(events_dir),
                "--results",
                str(results_path),
                "--require-through",
                str(args.require_through),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            print(proc.stderr or proc.stdout, file=sys.stderr)
            return proc.returncode

    try:
        payloads, missing = gather_section11_rows(
            events_dir, results_path, require_through=args.require_through
        )
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1

    if missing:
        print(f"ERROR {missing} JSONL file(s) lack diagnostic", file=sys.stderr)
        return 1

    try:
        original = report_path.read_text(encoding="utf-8")
        updated, changed = apply_section11_patch(
            original,
            payloads,
            require_through=args.require_through,
            events_dir=events_dir,
        )
    except ValueError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1

    if changed == 0:
        if args.dry_run:
            print(
                f"OK dry-run: no changes needed in {report_path} "
                "(§11 / §2.1 already match artifacts)"
            )
            return 0
        print("WARN no §11 table rows updated (check row ids 1–14)", file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"OK dry-run: would update {changed} row(s) in {report_path}")
        return 0

    report_path.write_text(updated, encoding="utf-8")
    print(f"OK patched {changed} row(s) in {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
