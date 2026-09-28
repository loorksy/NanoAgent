"""Same-origin view of the MetaTrader window.

The desktop password stays on the server. Only a signed-in Mokli session
can open the window or its VNC socket.
"""

from __future__ import annotations

import asyncio
import inspect

import httpx
import websockets
from fastapi import APIRouter, Depends, WebSocket
from fastapi.responses import JSONResponse, Response
from mokli_ui.utils.auth import get_verified_user, get_verified_user_by_token
from starlette.requests import Request
from websockets.exceptions import ConnectionClosed

from mokli.surface.mt5_desktop import desktop_authorization, upstream_http_url, upstream_ws_url

http_router = APIRouter()
ws_router = APIRouter()

_DROP_HEADERS = {
    'connection',
    'keep-alive',
    'proxy-authenticate',
    'proxy-authorization',
    'te',
    'trailers',
    'transfer-encoding',
    'upgrade',
    'content-encoding',
    'content-length',
    'www-authenticate',
}


def _unavailable() -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={'error': {'details': {'message': 'MetaTrader window is not configured'}}},
    )


async def _proxy_http(path: str, request: Request) -> Response:
    authorization = desktop_authorization()
    if authorization is None:
        return _unavailable()
    headers = {'Authorization': authorization}
    content_type = request.headers.get('content-type')
    if content_type:
        headers['Content-Type'] = content_type
    body = await request.body()
    url = upstream_http_url(path, request.url.query)
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
            upstream = await client.request(
                request.method,
                url,
                content=body or None,
                headers=headers,
            )
    except httpx.HTTPError:
        return _unavailable()
    if upstream.status_code == 401:
        return _unavailable()
    passed = {
        key: value
        for key, value in upstream.headers.items()
        if key.lower() not in _DROP_HEADERS
    }
    media = passed.pop('content-type', None)
    return Response(content=upstream.content, status_code=upstream.status_code, headers=passed, media_type=media)


@http_router.api_route('', methods=['GET', 'HEAD'])
@http_router.api_route('/', methods=['GET', 'HEAD'])
@http_router.api_route('/{path:path}', methods=['GET', 'HEAD', 'POST', 'PUT', 'DELETE'])
async def desktop_http(
    request: Request,
    path: str = '',
    user=Depends(get_verified_user),
) -> Response:
    del user
    return await _proxy_http(path, request)


def _connect_headers(authorization: str) -> dict[str, object]:
    params = inspect.signature(websockets.connect).parameters
    key = 'additional_headers' if 'additional_headers' in params else 'extra_headers'
    return {key: {'Authorization': authorization}, 'max_size': None, 'open_timeout': 10}


async def _browser_to_terminal(websocket: WebSocket, upstream) -> None:
    while True:
        message = await websocket.receive()
        if message.get('type') == 'websocket.disconnect':
            return
        if message.get('bytes') is not None:
            await upstream.send(message['bytes'])
        elif message.get('text') is not None:
            await upstream.send(message['text'])


async def _terminal_to_browser(websocket: WebSocket, upstream) -> None:
    async for message in upstream:
        if isinstance(message, bytes):
            await websocket.send_bytes(message)
        else:
            await websocket.send_text(message)


async def _bridge_socket(websocket: WebSocket, upstream) -> None:
    done, pending = await asyncio.wait(
        {
            asyncio.create_task(_browser_to_terminal(websocket, upstream)),
            asyncio.create_task(_terminal_to_browser(websocket, upstream)),
        },
        return_when=asyncio.FIRST_COMPLETED,
    )
    for task in pending:
        task.cancel()
    for task in done:
        task.result()


@ws_router.websocket('/websockify')
async def desktop_socket(websocket: WebSocket) -> None:
    token = websocket.cookies.get('token') or ''
    user = await get_verified_user_by_token(token)
    if user is None:
        await websocket.close(code=4401)
        return
    authorization = desktop_authorization()
    if authorization is None:
        await websocket.close(code=1011)
        return
    offered = list(websocket.scope.get('subprotocols') or [])
    try:
        upstream = await websockets.connect(
            upstream_ws_url(),
            subprotocols=offered,
            **_connect_headers(authorization),
        )
    except Exception:
        await websocket.close(code=1011)
        return
    chosen = upstream.subprotocol if upstream.subprotocol in offered else None
    await websocket.accept(subprotocol=chosen)
    try:
        await _bridge_socket(websocket, upstream)
    except (ConnectionClosed, RuntimeError):
        pass
    finally:
        await upstream.close()
