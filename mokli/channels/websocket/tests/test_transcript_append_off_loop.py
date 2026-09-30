"""A chat reply must not fsync its transcript on the event loop."""

from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from mokli.bus.events import OutboundMessage
from mokli.channels.websocket.runtime import WebSocketChannel, WebSocketConfig
from mokli.surface.gateway_services import build_gateway_services
from mokli.surface.transcript import append_transcript_object, read_transcript_lines


def _channel(bus: Any, workspace: Path) -> WebSocketChannel:
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
        static_dist_path=None,
        workspace_path=workspace,
        default_restrict_to_workspace=False,
        runtime_model_name=None,
        runtime_surface="browser",
        runtime_capabilities_overrides=None,
    )
    return WebSocketChannel(cfg, bus, gateway=gateway)


async def test_answer_transcript_write_leaves_the_event_loop_free(
    tmp_path: Path, monkeypatch,
) -> None:
    monkeypatch.setattr("mokli.config.paths.get_data_dir", lambda: tmp_path)
    order: list[str] = []
    real = append_transcript_object

    def slow(session_key: str, obj: dict[str, Any]) -> None:
        time.sleep(0.2)
        order.append(
            "main" if threading.current_thread() is threading.main_thread() else "worker"
        )
        real(session_key, obj)

    monkeypatch.setattr("mokli.surface.transcript.append_transcript_object", slow)
    channel = _channel(MagicMock(), tmp_path)

    async def tick() -> None:
        await asyncio.sleep(0.05)
        order.append("tick")

    pending = asyncio.create_task(tick())
    started = time.perf_counter()
    await channel.send(
        OutboundMessage(channel="websocket", chat_id="desk", content="saved-off-loop")
    )
    await pending
    assert order[0] == "tick"
    assert "main" not in order
    assert order.count("worker") == 1
    assert time.perf_counter() - started < 0.35
    lines = read_transcript_lines("websocket:desk")
    assert any(row.get("text") == "saved-off-loop" for row in lines)


async def test_stream_delta_does_not_write_the_transcript(
    tmp_path: Path, monkeypatch,
) -> None:
    monkeypatch.setattr("mokli.config.paths.get_data_dir", lambda: tmp_path)
    called: list[str] = []

    def record(session_key: str, obj: dict[str, Any]) -> None:
        called.append(str(obj.get("event")))

    monkeypatch.setattr("mokli.surface.transcript.append_transcript_object", record)
    channel = _channel(MagicMock(), tmp_path)
    await channel.send_delta("desk", "tok")
    assert called == []
