#!/usr/bin/env python3
"""Print OpenRouter daily reset time from a §11 quota-probe JSONL (stderr hint)."""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

_RESET_MS = re.compile(r"X-RateLimit-Reset['\"]:\s*['\"]?(\d+)")


def reset_epoch_ms_from_probe(path: Path) -> int | None:
    if not path.is_file():
        return None
    best: int | None = None
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if event.get("kind") != "delta":
            continue
        text = str((event.get("data") or {}).get("text") or "")
        for match in _RESET_MS.finditer(text):
            value = int(match.group(1))
            if value > 0:
                best = value if best is None else max(best, value)
    return best


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: section11_quota_reset_hint.py PROBE.jsonl", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    reset_ms = reset_epoch_ms_from_probe(path)
    if reset_ms is None:
        return 0
    reset_s = reset_ms // 1000 if reset_ms > 10_000_000_000 else reset_ms
    when = datetime.fromtimestamp(reset_s, tz=UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(
        f"HINT: OpenRouter free-tier daily reset ≈{when} (X-RateLimit-Reset; or add credits)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
