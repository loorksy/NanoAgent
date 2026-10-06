"""Address of the MetaTrader window served by the terminal container.

The browser never receives the desktop password. The UI proxy adds it.
"""

from __future__ import annotations

import base64
import os
from urllib.parse import urlsplit, urlunsplit


def desktop_base_url() -> str:
    raw = os.environ.get("MT5_DESKTOP_URL", "http://127.0.0.1:32768").strip()
    return raw.rstrip("/") or "http://127.0.0.1:32768"


def desktop_authorization() -> str | None:
    user = os.environ.get("MT5_DESKTOP_USER", "")
    password = os.environ.get("MT5_DESKTOP_PASSWORD", "")
    if not user or not password:
        return None
    token = base64.b64encode(f"{user}:{password}".encode()).decode("ascii")
    return f"Basic {token}"


def upstream_http_url(path: str, query: str) -> str:
    suffix = path.lstrip("/")
    target = f"{desktop_base_url()}/{suffix}" if suffix else f"{desktop_base_url()}/"
    if query:
        target = f"{target}?{query}"
    return target


def upstream_ws_url() -> str:
    parts = urlsplit(desktop_base_url())
    scheme = "wss" if parts.scheme == "https" else "ws"
    return urlunsplit((scheme, parts.netloc, "/websockify", "", ""))
