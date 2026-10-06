"""Stable mapping between public Mokli chat IDs and persisted session keys."""

from __future__ import annotations

import re
from typing import Any, TypeGuard

MOKLI_SESSION_STORAGE_PREFIX = "websocket:"
_MOKLI_CHAT_ID_RE = re.compile(r"^[A-Za-z0-9_:-]{1,64}$")


def is_valid_mokli_chat_id(value: Any) -> TypeGuard[str]:
    """Validate the compact chat IDs accepted by the Mokli protocol."""
    return isinstance(value, str) and _MOKLI_CHAT_ID_RE.fullmatch(value) is not None


def mokli_session_key(chat_id: str) -> str:
    """Return the backward-compatible persisted key for a Mokli chat."""
    return f"{MOKLI_SESSION_STORAGE_PREFIX}{chat_id}"


def is_mokli_session_key(session_key: str) -> bool:
    """Return whether *session_key* belongs to the Mokli session namespace."""
    return session_key.startswith(MOKLI_SESSION_STORAGE_PREFIX)


def mokli_chat_id(session_key: str) -> str | None:
    """Extract a non-empty Mokli chat ID from a persisted session key."""
    if not is_mokli_session_key(session_key):
        return None
    chat_id = session_key.removeprefix(MOKLI_SESSION_STORAGE_PREFIX)
    return chat_id or None
