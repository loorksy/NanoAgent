"""Unit tests for the Claude Code CLI provider. Never invoke a real `claude` binary."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from nanobot.config.schema import Config
from nanobot.providers.claude_code_cli import (
    ClaudeCodeCliProvider,
    messages_to_prompt,
    parse_cli_json,
    reset_cli_semaphore_for_tests,
)
from nanobot.providers.factory import make_provider, validate_provider_setup
from nanobot.providers.registry import find_by_name


def test_registry_and_factory_do_not_require_api_key() -> None:
    spec = find_by_name("claude-code-cli")
    assert spec is not None
    assert spec.name == "claude_code_cli"
    assert spec.backend == "claude_code_cli"
    assert spec.is_direct is True

    config = Config()
    config.agents.defaults.model = "sonnet"
    config.agents.defaults.provider = "claude_code_cli"
    validate_provider_setup(config)
    provider = make_provider(config)
    assert isinstance(provider, ClaudeCodeCliProvider)
    assert provider.get_default_model() == "sonnet"


def test_parse_cli_json_maps_usage_and_ignores_subscription_usd() -> None:
    response = parse_cli_json(
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "result": "hello from cli",
            "total_cost_usd": 1.23,
            "usage": {
                "input_tokens": 11,
                "output_tokens": 7,
                "cache_read_input_tokens": 2,
            },
        }
    )
    assert response.content == "hello from cli"
    assert response.finish_reason == "stop"
    assert response.usage is not None
    assert response.usage.input_tokens == 11
    assert response.usage.output_tokens == 7
    assert response.usage.cache_read_tokens == 2
    assert response.usage.reported_tokens == response.usage.total_tokens


def test_parse_cli_json_auth_error() -> None:
    response = parse_cli_json({"is_error": True, "result": "Error: not logged in"})
    assert response.finish_reason == "error"
    assert response.error_kind == "auth"


def test_messages_to_prompt_flattens_roles() -> None:
    prompt = messages_to_prompt(
        [
            {"role": "system", "content": "Be brief."},
            {"role": "user", "content": [{"type": "text", "text": "Price of gold?"}]},
        ]
    )
    assert "SYSTEM:" in prompt
    assert "USER:" in prompt
    assert "Price of gold?" in prompt


@pytest.mark.asyncio
async def test_chat_parses_runner_json() -> None:
    reset_cli_semaphore_for_tests()

    async def runner(**kwargs: Any):
        assert kwargs["binary"] == "claude"
        assert "hello" in kwargs["prompt"]
        assert kwargs["model"] == "sonnet"
        return parse_cli_json(
            json.dumps({"result": "ok", "usage": {"input_tokens": 1, "output_tokens": 1}})
        )

    provider = ClaudeCodeCliProvider(runner=runner, default_model="sonnet")
    response = await provider.chat(messages=[{"role": "user", "content": "hello"}])
    assert response.content == "ok"
    assert response.usage is not None
    assert response.usage.output_tokens == 1


@pytest.mark.asyncio
async def test_missing_cli_error_path() -> None:
    reset_cli_semaphore_for_tests()

    async def runner(**kwargs: Any):
        raise FileNotFoundError(kwargs["binary"])

    provider = ClaudeCodeCliProvider(runner=runner)
    response = await provider.chat(messages=[{"role": "user", "content": "hi"}])
    assert response.finish_reason == "error"
    assert response.error_kind == "missing_cli"
    assert "not found" in (response.content or "").lower()
    assert "ANTHROPIC_API_KEY" in (response.content or "")


@pytest.mark.asyncio
async def test_unauthenticated_cli_error_path() -> None:
    reset_cli_semaphore_for_tests()

    async def runner(**kwargs: Any):
        return parse_cli_json({"is_error": True, "result": "Please run /login"})

    provider = ClaudeCodeCliProvider(runner=runner)
    response = await provider.chat(messages=[{"role": "user", "content": "hi"}])
    assert response.finish_reason == "error"
    assert response.error_kind == "auth"


@pytest.mark.asyncio
async def test_timeout_error_path() -> None:
    reset_cli_semaphore_for_tests()

    async def runner(**kwargs: Any):
        raise asyncio.TimeoutError()

    provider = ClaudeCodeCliProvider(runner=runner, timeout_s=12)
    response = await provider.chat(messages=[{"role": "user", "content": "hi"}])
    assert response.finish_reason == "error"
    assert response.error_kind == "timeout"
    assert "12" in (response.content or "")


@pytest.mark.asyncio
async def test_concurrency_limit() -> None:
    reset_cli_semaphore_for_tests()
    current = 0
    peak = 0
    lock = asyncio.Lock()

    async def runner(**kwargs: Any):
        nonlocal current, peak
        async with lock:
            current += 1
            peak = max(peak, current)
        await asyncio.sleep(0.05)
        async with lock:
            current -= 1
        return parse_cli_json({"result": "done"})

    provider = ClaudeCodeCliProvider(runner=runner, max_concurrent=2)
    results = await asyncio.gather(
        *[provider.chat(messages=[{"role": "user", "content": f"n{i}"}]) for i in range(5)]
    )
    assert [r.content for r in results] == ["done"] * 5
    assert peak <= 2
    reset_cli_semaphore_for_tests()
