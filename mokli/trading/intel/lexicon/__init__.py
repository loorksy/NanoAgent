"""Keyword lexicons for the intel engines — data files, not code.

Each ``<name>.json`` in this directory is a JSON array of lowercase phrases.
``load(name)`` returns them as a cached ``frozenset``.
"""

from __future__ import annotations

import json
import re
from functools import cache
from pathlib import Path
from typing import cast

_LEXICON_DIR = Path(__file__).resolve().parent
_NAME_RE = re.compile(r"^[a-z0-9_]+$")


def available() -> tuple[str, ...]:
    """Names of every lexicon shipped in this directory (sorted)."""
    return tuple(sorted(path.stem for path in _LEXICON_DIR.glob("*.json")))


@cache
def load(name: str) -> frozenset[str]:
    """Return the phrase set for ``name`` (``<name>.json``); raises if missing."""
    if not _NAME_RE.match(name):
        raise ValueError(f"invalid lexicon name: {name!r}")
    path = _LEXICON_DIR / f"{name}.json"
    if not path.is_file():
        raise FileNotFoundError(f"lexicon not found: {name}")
    raw: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"lexicon {name} must be a JSON array")
    phrases: set[str] = set()
    for item in cast(list[object], raw):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"lexicon {name}: entries must be non-empty strings")
        phrases.add(item)
    return frozenset(phrases)


def alternation(name: str) -> re.Pattern[str]:
    """Case-insensitive ``\\b(a|b|…)\\b`` regex built from a lexicon (longest first)."""
    phrases = sorted(load(name), key=lambda phrase: (-len(phrase), phrase))
    body = "|".join(re.escape(phrase) for phrase in phrases)
    return re.compile(rf"\b({body})\b", re.IGNORECASE)


__all__ = ["alternation", "available", "load"]
