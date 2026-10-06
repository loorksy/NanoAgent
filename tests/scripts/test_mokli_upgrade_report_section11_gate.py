"""§11 production closure gate on docs/mokli-agent-upgrade-report.md."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "docs" / "mokli-agent-upgrade-report.md"
_ROW = re.compile(r"^\|\s*(\d+)\s*\|")


def _live_section11_table(text: str) -> tuple[str, dict[int, tuple[str, str]]]:
    header = ""
    rows: dict[int, tuple[str, str]] = {}
    in_section = False
    for line in text.splitlines():
        if line.startswith("## 11. مسارات حية"):
            in_section = True
            header = line
            continue
        if in_section and line.startswith("### 11.1"):
            break
        if not in_section:
            continue
        match = _ROW.match(line)
        if not match:
            continue
        row_id = int(match.group(1))
        parts = line.split("|")
        if len(parts) < 8:
            continue
        rows[row_id] = (parts[5].strip(), parts[6].strip())
    return header, rows


def test_section11_either_pending_or_vps_filled() -> None:
    text = REPORT.read_text(encoding="utf-8")
    header, rows = _live_section11_table(text)
    assert header
    core_rows = range(1, 14)  # rows 1–13 required for production; 14 optional (MT5)
    assert all(row_id in rows for row_id in core_rows)
    assert 14 in rows, "optional MT5 row should remain in §11 table"

    pending = "Cloud Agent" in header and "تعبئة جزئية" not in header and "تم التعبئة من تشغيل VPS" not in header
    partial = "تعبئة جزئية" in header
    filled = "تم التعبئة من تشغيل VPS" in header and not partial

    assert pending or partial or filled, f"unexpected §11 header: {header!r}"

    if pending:
        for row_id in core_rows:
            result, numbers = rows[row_id]
            assert not result and not numbers, f"row {row_id} must stay empty until VPS fill"
    elif partial:
        any_fill = any(rows[row_id][0].strip() for row_id in core_rows)
        assert any_fill, "partial §11 header requires at least one filled row"
        for row_id in core_rows:
            result, numbers = rows[row_id]
            if result.strip() or numbers.strip():
                assert result.strip() and numbers.strip(), f"row {row_id} needs both columns"
                assert "dry-run" not in result.lower(), f"row {row_id} still placeholder"
    else:
        for row_id in core_rows:
            result, numbers = rows[row_id]
            assert result and numbers, f"row {row_id} missing VPS fill"
            assert "dry-run" not in result.lower(), f"row {row_id} still placeholder"
        # Row 14 (MT5) may stay empty when operator closes with --require-through 13.
