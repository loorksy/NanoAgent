"""Operator locale helpers for trading output."""

from __future__ import annotations

import re

_ARABIC_RE = re.compile(r"[\u0600-\u06FF]")


def locale_from_text(text: str) -> str:
    """Return ``ar`` when operator text contains Arabic script, else ``en``."""
    return "ar" if _ARABIC_RE.search(text or "") else "en"


def normalize_locale(locale: str | None) -> str:
    if locale and str(locale).lower().startswith("ar"):
        return "ar"
    return "en"


def resolve_locale(payload: dict | None = None, *, locale: str | None = None) -> str:
    if locale:
        return normalize_locale(locale)
    if payload and payload.get("locale"):
        return normalize_locale(str(payload["locale"]))
    return "en"
