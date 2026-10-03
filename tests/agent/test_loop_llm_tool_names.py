"""AgentLoop passes task-scoped tool schemas to AgentRunner (P0 light turns)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from mokli.agent.context import TranscriptInput
from mokli.agent.loop import AgentLoop
from mokli.agent.runner import AgentRunResult, AgentRunSpec
from mokli.bus.queue import MessageBus
from mokli.providers.base import LLMResponse


@pytest.mark.asyncio
async def test_greeting_defers_trading_tool_schemas(tmp_path) -> None:
    captured: list[AgentRunSpec] = []

    async def fake_run(spec: AgentRunSpec) -> AgentRunResult:
        captured.append(spec)
        return AgentRunResult(final_content="ok", messages=[])

    provider = MagicMock()
    provider.get_default_model.return_value = "test-model"
    provider.chat_stream_with_retry = AsyncMock(
        return_value=LLMResponse(content="ok", tool_calls=[]),
    )

    loop = AgentLoop(
        bus=MessageBus(),
        provider=provider,
        workspace=tmp_path,
        model="test-model",
    )
    loop.runner.run = fake_run  # type: ignore[method-assign]
    runtime = loop.llm_runtime()

    await loop._run_agent_loop(
        TranscriptInput(history=[], current_message="مرحبا"),
        runtime=runtime,
        ephemeral=True,
    )
    assert len(captured) == 1
    light_names = captured[0].llm_tool_names
    assert light_names is not None
    assert "run_trading_kernel" not in light_names
    assert "get_gold_quote" not in light_names
    assert "message" in light_names

    await loop._run_agent_loop(
        TranscriptInput(history=[], current_message="حلل الذهب"),
        runtime=runtime,
        ephemeral=True,
    )
    full_names = captured[1].llm_tool_names
    assert full_names is not None
    assert "run_trading_kernel" in full_names
    assert len(full_names) > len(light_names)
