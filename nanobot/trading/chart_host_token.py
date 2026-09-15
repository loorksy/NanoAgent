"""HMAC tokens for the isolated /chart-host page (Playwright sidecar)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time

_TOKEN_KIND = "chart-host"
_DEFAULT_TTL_SEC = 6 * 60 * 60


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


def chart_host_control_secret() -> str | None:
    for name in ("CHART_HOST_CONTROL_TOKEN", "NANOBOT_CHART_HOST_TOKEN", "AICHART_SERVICE_TOKEN"):
        value = os.environ.get(name, "").strip()
        if value and len(value) >= 16:
            return value
    return None


def mint_chart_host_page_token(ttl_sec: int = _DEFAULT_TTL_SEC) -> str | None:
    secret = chart_host_control_secret()
    if not secret:
        return None
    expires_at = int(time.time()) + max(60, ttl_sec)
    payload = f"{_TOKEN_KIND}:{expires_at}"
    digest = hmac.new(secret.encode("utf-8"), payload.encode("ascii"), hashlib.sha256).digest()[:16]
    return _b64url_encode(f"{expires_at}.{_b64url_encode(digest)}".encode("ascii"))


def verify_chart_host_page_token(token: str) -> bool:
    secret = chart_host_control_secret()
    if not secret or not token.strip():
        return False
    try:
        decoded = _b64url_decode(token.strip()).decode("ascii")
        expires_text, provided_sig = decoded.split(".", 1)
        expires_at = int(expires_text)
    except (ValueError, UnicodeDecodeError):
        return False
    if expires_at < int(time.time()):
        return False
    payload = f"{_TOKEN_KIND}:{expires_at}"
    expected = hmac.new(secret.encode("utf-8"), payload.encode("ascii"), hashlib.sha256).digest()[:16]
    try:
        provided = _b64url_decode(provided_sig)
    except ValueError:
        return False
    return hmac.compare_digest(provided, expected)
