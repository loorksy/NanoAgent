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


def seconds_until_reset(path: Path) -> int | None:
    """Seconds until reset epoch; 0 if reset time passed; None if not found."""
    reset_ms = reset_epoch_ms_from_probe(path)
    if reset_ms is None:
        return None
    reset_s = reset_ms // 1000 if reset_ms > 10_000_000_000 else reset_ms
    import time

    return max(0, int(reset_s - time.time()))


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("probe", type=Path)
    parser.add_argument(
        "--seconds",
        action="store_true",
        help="Print seconds until reset on stdout (-1 if unknown)",
    )
    args = parser.parse_args()
    path = args.probe
    reset_ms = reset_epoch_ms_from_probe(path)
    if args.seconds:
        remaining = seconds_until_reset(path)
        print(-1 if remaining is None else remaining)
        return 0
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
