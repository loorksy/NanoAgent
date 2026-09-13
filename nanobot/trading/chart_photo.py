"""Persist chart snapshot bytes for channel delivery (Telegram photo)."""

from __future__ import annotations

import base64
import re
import tempfile
from pathlib import Path
from typing import Any

_DATA_URL_RE = re.compile(r"^data:image/(?P<fmt>[a-zA-Z0-9+.-]+);base64,(?P<data>.+)$", re.S)


def lead_chart_frame(frames: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    if not frames:
        return None
    for frame in frames:
        if isinstance(frame, dict) and (frame.get("image") or frame.get("dataUrl")):
            return frame
    return None


def write_chart_snapshot_file(frame: dict[str, Any] | None) -> str | None:
    if not frame:
        return None
    raw = frame.get("image") or frame.get("dataUrl")
    if not isinstance(raw, str) or not raw.strip():
        return None
    ext = "jpg"
    payload = raw.strip()
    if payload.startswith("data:"):
        match = _DATA_URL_RE.match(payload)
        if not match:
            return None
        fmt = match.group("fmt").lower()
        ext = "png" if fmt == "png" else "jpg"
        try:
            data = base64.b64decode(match.group("data"))
        except Exception:
            return None
    else:
        try:
            data = base64.b64decode(payload)
        except Exception:
            return None
    if not data:
        return None
    handle = tempfile.NamedTemporaryFile(
        prefix="nanobot-gold-chart-",
        suffix=f".{ext}",
        delete=False,
    )
    handle.write(data)
    handle.flush()
    handle.close()
    return handle.name


def cleanup_chart_snapshot(path: str | None) -> None:
    if not path:
        return
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        return
