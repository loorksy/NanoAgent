"""Resolve cross-channel delivery targets for proactive sends."""

from __future__ import annotations

import re

from nanobot.pairing.store import get_approved

_TELEGRAM_NUMERIC = re.compile(r"^\d+$")


def telegram_chat_id_from_sender(sender_id: str) -> str | None:
    """Extract the numeric Telegram chat id from a sender_id like 5969744996|username."""
    raw = (sender_id or "").strip()
    if not raw:
        return None
    head = raw.split("|", 1)[0].strip()
    return head if _TELEGRAM_NUMERIC.match(head) else None


def resolve_telegram_chat_id(chat_id: str | None) -> str | None:
    """Normalize a Telegram delivery target to a numeric chat id."""
    raw = (chat_id or "").strip()
    if not raw:
        return None
    if _TELEGRAM_NUMERIC.match(raw):
        return raw
    from_sender = telegram_chat_id_from_sender(raw)
    if from_sender:
        return from_sender
    return None


def default_telegram_chat_id() -> str | None:
    """Best-effort Telegram chat id for the primary approved operator."""
    approved = get_approved("telegram")
    for sender_id in approved:
        resolved = telegram_chat_id_from_sender(str(sender_id))
        if resolved:
            return resolved
    return None
