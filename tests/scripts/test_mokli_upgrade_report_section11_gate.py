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
    required = range(1, 14)
    assert all(row_id in rows for row_id in required)

    pending = "Cloud Agent" in header and "تم التعبئة من تشغيل VPS" not in header
    filled = "تم التعبئة من تشغيل VPS" in header

    assert pending or filled, f"unexpected §11 header: {header!r}"

    if pending:
        for row_id in range(1, 14):
            result, numbers = rows[row_id]
            assert not result and not numbers, f"row {row_id} must stay empty until VPS fill"
    else:
        for row_id in range(1, 14):
            result, numbers = rows[row_id]
            assert result and numbers, f"row {row_id} missing VPS fill"
            assert "dry-run" not in result.lower(), f"row {row_id} still placeholder"
