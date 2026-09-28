"""Server-side proxy from the Mokli session to the Mokli gateway.

The long-lived gateway token stays in ``MOKLI_API_TOKEN``. The browser
calls ``/api/v1/mokli/<gateway path>`` with its Mokli cookie.
"""

from __future__ import annotations

import os

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response

from mokli_ui.utils.auth import get_verified_user

router = APIRouter()


def _gateway_base() -> str:
    return os.environ.get("MOKLI_GATEWAY_URL", "http://127.0.0.1:8766").rstrip("/")


def _gateway_token() -> str:
    return os.environ.get("MOKLI_API_TOKEN", "")


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
    # A first MT5 login waits on the terminal. The default 30s proxy cuts that
    # off and the browser only sees "gateway 500".
    timeout = 90.0 if path.startswith("connect/mt5") else 30.0
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            upstream = await client.request(request.method, url, content=body or None, headers=headers)
    except httpx.TimeoutException:
        return JSONResponse(
            status_code=504,
            content={
                "error": {
                    "details": {
                        "message": "MT5 connection test timed out before the terminal answered",
                    }
                }
            },
        )
    media = upstream.headers.get("content-type")
    return Response(content=upstream.content, status_code=upstream.status_code, media_type=media)
