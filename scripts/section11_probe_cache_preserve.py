#!/usr/bin/env python3
"""Decide whether to restore a previous local quota-probe JSONL after a weak pull."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from section11_quota_reset_hint import seconds_until_reset


def _has_diagnostic(path: Path) -> bool:
    if not path.is_file():
        return False
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if event.get("kind") == "diagnostic":
            return True
    return False


def should_restore_probe_backup(new_path: Path, backup_path: Path) -> bool:
    """True when *new_path* lacks diagnostic and reset hint but *backup_path* is useful."""
    if not new_path.is_file() or not backup_path.is_file():
        return False
    if _has_diagnostic(new_path):
        return False
    if seconds_until_reset(new_path) is not None:
        return False
    if seconds_until_reset(backup_path) is not None:
        return True
    return _has_diagnostic(backup_path)


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: section11_probe_cache_preserve.py NEW_JSONL BACKUP_JSONL", file=sys.stderr)
        return 2
    new_path = Path(sys.argv[1])
    backup_path = Path(sys.argv[2])
    print("yes" if should_restore_probe_backup(new_path, backup_path) else "no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
