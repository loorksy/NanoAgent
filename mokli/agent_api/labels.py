"""Label catalog served by ``GET /labels`` and used by the HTML renderer.

Labels come from ``mokli/trading/locales/{locale}.json``; unknown keys fall
back to the key itself so no user-facing text is ever hard-coded here.
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import cast

LOCALES_DIR = Path(__file__).resolve().parents[1] / "trading" / "locales"
SUPPORTED_LOCALES: tuple[str, ...] = ("en", "ar")
RTL_LOCALES: frozenset[str] = frozenset({"ar", "he", "fa", "ur"})


def normalize_locale(locale: str | None) -> str:
    value = (locale or "en").strip().lower().replace("_", "-")
    base = value.split("-", 1)[0]
    return base if base in SUPPORTED_LOCALES else "en"


def text_direction(locale: str | None) -> str:
    return "rtl" if normalize_locale(locale) in RTL_LOCALES else "ltr"


@cache
def _load(locale: str, locales_dir: str) -> dict[str, str]:
    path = Path(locales_dir) / f"{locale}.json"
    if not path.exists():
        return {}
    try:
        raw: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {
        str(key): value
        for key, value in cast(dict[object, object], raw).items()
        if isinstance(value, str)
    }


def catalog(locale: str | None, *, locales_dir: Path | None = None) -> dict[str, str]:
    """Full flat catalog for ``locale`` (falls back to English entries for missing keys)."""
    loc = normalize_locale(locale)
    directory = str(locales_dir or LOCALES_DIR)
    merged = dict(_load("en", directory))
    if loc != "en":
        merged.update(_load(loc, directory))
    return merged


class Labels:
    """Callable label lookup bound to one locale: ``labels("label.result.price")``."""

    def __init__(self, locale: str | None, *, locales_dir: Path | None = None) -> None:
        self.locale = normalize_locale(locale)
        self.dir = text_direction(self.locale)
        self._catalog = catalog(self.locale, locales_dir=locales_dir)

    def get(self, key: str) -> str:
        return self._catalog.get(key, key)

    def __call__(self, key: str) -> str:
        return self.get(key)

    def has(self, key: str) -> bool:
        return key in self._catalog
