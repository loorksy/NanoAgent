"""Workspace preview, signed media, and page assets must not block the event loop."""

from __future__ import annotations

import asyncio
import json
import threading
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch
from urllib.parse import quote

from websockets.datastructures import Headers
from websockets.http11 import Request

from mokli.channels.websocket.runtime import WebSocketChannel, WebSocketConfig
from mokli.surface.gateway_services import build_gateway_services
from mokli.surface.media_api import sign_media_path
from mokli.surface.ws_http import file_preview_payload

_PNG = b"\x89PNG\r\n\x1a\npreview-off-loop"


def _channel(
    bus: Any,
    workspace: Path,
    *,
    static_dist_path: Path | None = None,
) -> WebSocketChannel:
    cfg: dict[str, Any] = {
        "enabled": True,
        "allowFrom": ["*"],
        "host": "127.0.0.1",
        "port": 29877,
        "path": "/ws",
        "websocketRequiresToken": False,
    }
    parsed = WebSocketConfig.model_validate(cfg)
    gateway = build_gateway_services(
        config=parsed,
        bus=bus,
        session_manager=None,
        static_dist_path=static_dist_path,
        workspace_path=workspace,
        default_restrict_to_workspace=False,
        runtime_model_name=None,
        runtime_surface="browser",
        runtime_capabilities_overrides=None,
    )
    return WebSocketChannel(cfg, bus, gateway=gateway)


def _mark(order: list[str]) -> None:
    order.append(
        "main" if threading.current_thread() is threading.main_thread() else "worker"
    )


async def _during(order: list[str], call):
    async def tick() -> None:
        await asyncio.sleep(0.05)
        order.append("tick")

    pending = asyncio.create_task(tick())
    started = time.perf_counter()
    response = await call
    await pending
    assert order[0] == "tick"
    assert "main" not in order
    assert order.count("worker") == 1
    assert time.perf_counter() - started < 0.35
    return response


async def test_file_preview_leaves_the_event_loop_free(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    source = workspace / "notes.md"
    source.parent.mkdir()
    source.write_text("preview-off-loop\n", encoding="utf-8")
    order: list[str] = []
    real = file_preview_payload

    def slow(*args, **kwargs):
        time.sleep(0.2)
        _mark(order)
        return real(*args, **kwargs)

    monkeypatch.setattr("mokli.surface.ws_http.file_preview_payload", slow)
    channel = _channel(MagicMock(), workspace)
    channel.gateway.tokens.api_tokens["tok"] = time.monotonic() + 300.0
    key = "websocket:desk"
    encoded = quote(key, safe="")
    path = quote("notes.md", safe="")
    request = Request(
        f"/api/sessions/{encoded}/file-preview?path={path}",
        Headers([("Authorization", "Bearer tok")]),
    )
    response = await _during(
        order,
        channel.gateway.http._dispatch_session_routes(
            request,
            f"/api/sessions/{encoded}/file-preview",
        ),
    )
    body = json.loads(response.body.decode())
    assert body["content"] == "preview-off-loop\n"


async def test_signed_media_leaves_the_event_loop_free(tmp_path: Path) -> None:
    media = tmp_path / "media"
    media.mkdir()
    target = media / "shot.png"
    target.write_bytes(_PNG)
    order: list[str] = []
    channel = _channel(MagicMock(), tmp_path)
    real_read = Path.read_bytes

    def slow(self: Path) -> bytes:
        if self.name == "shot.png":
            time.sleep(0.2)
            _mark(order)
        return real_read(self)

    with (
        patch("mokli.surface.media_gateway.get_media_dir", return_value=media),
        patch.object(Path, "read_bytes", slow),
    ):
        url = sign_media_path(
            target,
            secret=channel.gateway.media.secret,
            media_dir=channel.gateway.media._media_dir,
        )
        assert url is not None
        request = Request(url, Headers())
        response = await _during(
            order,
            channel.gateway.http._dispatch_resolved(MagicMock(), request, url),
        )
    assert response.body == _PNG


async def test_page_asset_leaves_the_event_loop_free(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<title>page-off-loop</title>", encoding="utf-8")
    order: list[str] = []
    channel = _channel(MagicMock(), tmp_path, static_dist_path=dist)
    real_read = Path.read_bytes

    def slow(self: Path) -> bytes:
        if self.name == "index.html":
            time.sleep(0.2)
            _mark(order)
        return real_read(self)

    with patch.object(Path, "read_bytes", slow):
        request = Request("/", Headers())
        response = await _during(
            order,
            channel.gateway.http._dispatch_resolved(MagicMock(), request, "/"),
        )
    assert b"page-off-loop" in response.body
