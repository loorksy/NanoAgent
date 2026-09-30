"""The end-of-turn transcript rewrite must not block the event loop."""

from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from mokli.agent.context import TranscriptInput
from mokli.agent.loop import AgentLoop
from mokli.agent.runner import AgentRunResult
from mokli.bus.events import InboundMessage
from mokli.bus.queue import MessageBus
from mokli.session.mokli_turns import MokliTurnCoordinator


def _result(final_content: str, messages: list[dict]) -> AgentRunResult:
    return AgentRunResult(
        final_content=final_content,
        messages=messages,
        stop_reason="stop",
        had_injections=False,
        usage=None,
    )


def _loop(tmp_path: Path) -> AgentLoop:
    provider = MagicMock()
    provider.get_default_model.return_value = "test-model"
    provider.generation = SimpleNamespace(max_tokens=4096)
    provider.chat_stream_with_retry = AsyncMock()
    loop = AgentLoop(bus=MessageBus(), provider=provider, workspace=tmp_path, model="test-model")
    MokliTurnCoordinator(
        bus=loop.bus,
        sessions=loop.sessions,
        schedule_background=lambda coro: loop.schedule_background(coro),
    ).subscribe()
    return loop


async def test_turn_transcript_write_leaves_the_event_loop_free(
    tmp_path: Path, monkeypatch,
) -> None:
    loop = _loop(tmp_path)
    order: list[str] = []
    real = loop.sessions.persist_to_disk

    def slow(session, *, fsync: bool = False) -> bool:
        time.sleep(0.2)
        order.append(
            "main" if threading.current_thread() is threading.main_thread() else "worker"
        )
        return real(session, fsync=fsync)

    monkeypatch.setattr(loop.sessions, "persist_to_disk", slow)

    async def fake_run(transcript_input: TranscriptInput, **_kwargs: object) -> AgentRunResult:
        initial = loop.context.build_transcript(transcript_input, include_memory=False)
        return _result("saved-off-loop", [*initial, {"role": "assistant", "content": "saved-off-loop"}])

    loop._run_agent_loop = fake_run  # type: ignore[method-assign]

    async def tick() -> None:
        await asyncio.sleep(0.05)
        order.append("tick")

    pending = asyncio.create_task(tick())
    started = time.perf_counter()
    await loop._process_message(
        InboundMessage(channel="cli", sender_id="user", chat_id="desk", content="hello gold")
    )
    await pending
    assert order[0] == "tick"
    assert "main" not in order
    # The user message is written before the model, then the finished turn
    # rewrites the file. Both sleeps run on a worker.
    assert order.count("worker") == 2
    assert time.perf_counter() - started < 0.65

    loop.sessions.invalidate("cli:desk")
    persisted = loop.sessions.get_or_create("cli:desk")
    assert any(message.get("content") == "saved-off-loop" for message in persisted.messages)
    assert loop.sessions.get_cached("cli:desk") is persisted
