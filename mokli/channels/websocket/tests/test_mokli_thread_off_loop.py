"""Opening a chat transcript must not block the event loop."""

from __future__ import annotations

import asyncio
import json
import threading
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock
from urllib.parse import quote

from websockets.datastructures import Headers
from websockets.http11 import Request

from mokli.channels.websocket.runtime import WebSocketChannel, WebSocketConfig
from mokli.surface.gateway_services import build_gateway_services
from mokli.surface.transcript import append_transcript_object, read_transcript_lines


def _channel(bus: Any, workspace: Path) -> WebSocketChannel:
    cfg: dict[str, Any] = {
        "enabled": True,
        "allowFrom": ["*"],
        "host": "127.0.0.1",
        "port": 29876,
        "path": "/ws",
        "websocketRequiresToken": False,
    }
    parsed = WebSocketConfig.model_validate(cfg)
    gateway = build_gateway_services(
        config=parsed,
        bus=bus,
        session_manager=None,
        static_dist_path=None,
        workspace_path=workspace,
        default_restrict_to_workspace=False,
        runtime_model_name=None,
        runtime_surface="browser",
        runtime_capabilities_overrides=None,
    )
    return WebSocketChannel(cfg, bus, gateway=gateway)


async def test_mokli_thread_get_leaves_the_event_loop_free(
    tmp_path: Path, monkeypatch,
) -> None:
    monkeypatch.setattr("mokli.config.paths.get_data_dir", lambda: tmp_path)
    key = "websocket:desk"
    append_transcript_object(key, {"event": "user", "chat_id": "desk", "text": "opened-off-loop"})

    order: list[str] = []
    real = read_transcript_lines

    def slow(session_key: str):
        time.sleep(0.2)
        order.append(
            "main" if threading.current_thread() is threading.main_thread() else "worker"
        )
        return real(session_key)

    monkeypatch.setattr("mokli.surface.transcript.read_transcript_lines", slow)

    channel = _channel(MagicMock(), tmp_path)
    channel.gateway.tokens.api_tokens["tok"] = time.monotonic() + 300.0
    encoded = quote(key, safe="")
    request = Request(
        f"/api/sessions/{encoded}/mokli-thread",
        Headers([("Authorization", "Bearer tok")]),
    )

    async def tick() -> None:
        await asyncio.sleep(0.05)
        order.append("tick")

    pending = asyncio.create_task(tick())
    started = time.perf_counter()
    response = await channel.gateway.http._dispatch_session_routes(
        request,
        f"/api/sessions/{encoded}/mokli-thread",
    )
    await pending
    assert order[0] == "tick"
    assert "main" not in order
    assert order.count("worker") == 1
    assert time.perf_counter() - started < 0.35
    assert response is not None
    body = json.loads(response.body.decode())
    assert body["messages"][0]["content"] == "opened-off-loop"
