"""Operator locale helpers for trading output."""

from __future__ import annotations

import re

_ARABIC_RE = re.compile(r"[\u0600-\u06FF]")


def locale_from_text(text: str) -> str:
    """Return ``ar`` when operator text contains Arabic script, else ``en``."""
    return "ar" if _ARABIC_RE.search(text or "") else "en"


def active_locale(text: str | None = None) -> str:
    """Prefer the locale the UI sent on this turn, then the script of the text."""
    from nanobot.agent.tools.context import current_request_context

    ctx = current_request_context()
    if ctx is not None:
        raw = ctx.attributes.get("locale") if isinstance(ctx.attributes, dict) else None
        if isinstance(raw, str) and raw.strip():
            return normalize_locale(raw)
        if text is None:
            text = ctx.original_user_text or ""
    return locale_from_text(text or "")


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
