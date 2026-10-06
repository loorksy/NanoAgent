"""Legacy Mokli JSON snapshot path helpers (JSON file); transcripts use transcript."""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from mokli.config.paths import get_mokli_dir
from mokli.session.manager import SessionManager
from mokli.surface.transcript import delete_mokli_transcript


def mokli_thread_file_path(session_key: str) -> Path:
    stem = SessionManager.safe_key(session_key)
    return get_mokli_dir() / f"{stem}.json"


def delete_mokli_thread(session_key: str) -> bool:
    """Remove legacy Mokli JSON snapshot and append-only transcript for *session_key*."""
    removed = False
    path = mokli_thread_file_path(session_key)
    if path.is_file():
        try:
            path.unlink()
            removed = True
        except OSError as e:
            logger.warning("Failed to delete mokli thread file {}: {}", path, e)
    if delete_mokli_transcript(session_key):
        removed = True
    return removed
