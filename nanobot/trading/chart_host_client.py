"""HTTP client for the optional chart-host Playwright sidecar."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urljoin

from nanobot.trading.chart_host_token import chart_host_control_secret, mint_chart_host_page_token


def chart_host_url() -> str | None:
    raw = os.environ.get("CHART_HOST_URL", "").strip().rstrip("/")
    return raw or None


def chart_host_app_origin() -> str | None:
    for name in ("CHART_HOST_APP_URL", "NANOBOT_PUBLIC_URL", "APP_URL"):
        raw = os.environ.get(name, "").strip().rstrip("/")
        if raw:
            return raw
    return None


def build_chart_host_page_url() -> str | None:
    origin = chart_host_app_origin()
    token = mint_chart_host_page_token()
    if not origin or not token:
        return None
    return f"{origin}/chart-host?token={token}"


def _control_headers() -> dict[str, str]:
    secret = chart_host_control_secret()
    if not secret:
        raise RuntimeError("chart-host control token is not configured")
    return {
        "Authorization": f"Bearer {secret}",
        "Content-Type": "application/json",
    }


def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=_control_headers(), method="POST")
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


async def ensure_chart_host_tab() -> bool:
    """Keep the Playwright chart-host tab warm. Returns False when unavailable."""
    host = chart_host_url()
    page_url = build_chart_host_page_url()
    if not host or not page_url:
        return False
    endpoint = urljoin(f"{host}/", "session/ensure")
    try:
        import asyncio

        result = await asyncio.to_thread(_post_json, endpoint, {"pageUrl": page_url})
        return bool(result.get("ok"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, RuntimeError):
        return False
