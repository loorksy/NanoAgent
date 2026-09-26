"""Server-side proxy from the Open WebUI session to the NanoAgent gateway.

The long-lived gateway token stays in ``NANOAGENT_API_TOKEN``. The browser
calls ``/api/v1/nanoagent/<gateway path>`` with its Open WebUI cookie.
"""

from __future__ import annotations

import os

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from open_webui.utils.auth import get_verified_user

router = APIRouter()


def _gateway_base() -> str:
    return os.environ.get("NANOAGENT_GATEWAY_URL", "http://127.0.0.1:8766").rstrip("/")


def _gateway_token() -> str:
    return os.environ.get("NANOAGENT_API_TOKEN", "")


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def forward(
    path: str,
    request: Request,
    user=Depends(get_verified_user),
) -> Response:
    del user
    url = f"{_gateway_base()}/api/v2/{path}"
    if request.url.query:
        url = f"{url}?{request.url.query}"
    headers: dict[str, str] = {}
    token = _gateway_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    content_type = request.headers.get("content-type")
    if content_type:
        headers["Content-Type"] = content_type
    body = await request.body()
    async with httpx.AsyncClient(timeout=30.0) as client:
        upstream = await client.request(request.method, url, content=body or None, headers=headers)
    media = upstream.headers.get("content-type")
    return Response(content=upstream.content, status_code=upstream.status_code, media_type=media)
