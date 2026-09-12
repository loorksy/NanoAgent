"""Claude Code CLI provider — local `claude` binary, no ANTHROPIC_API_KEY.

This backend shells out to the already-authenticated Claude Code CLI
(`claude -p … --output-format json`). Billing is the host's Claude Code
subscription: token counts are reported when the CLI exposes them, but
there is no per-token dollar estimate (LLMUsage has no cost field).
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
from contextlib import suppress
from typing import Any

from loguru import logger

from nanobot.providers.base import LLMProvider, LLMResponse, LLMUsage

_DEFAULT_TIMEOUT_S = 90.0
_DEFAULT_MAX_CONCURRENT = 2
_DEFAULT_BINARY = "claude"

_AUTH_MARKERS = (
    "not logged in",
    "not authenticated",
    "please run /login",
    "please run claude login",
    "authentication_error",
    "unauthorized",
    "invalid api key",
)

# Process-wide cap so swarm/orchestrator cannot spawn unbounded `claude` processes.
_SEMAPHORE: asyncio.Semaphore | None = None
_SEMAPHORE_LIMIT: int | None = None


def reset_cli_semaphore_for_tests() -> None:
    """Drop the module semaphore so unit tests can change the concurrency cap."""
    global _SEMAPHORE, _SEMAPHORE_LIMIT
    _SEMAPHORE = None
    _SEMAPHORE_LIMIT = None


def _cli_semaphore(limit: int) -> asyncio.Semaphore:
    global _SEMAPHORE, _SEMAPHORE_LIMIT
    if _SEMAPHORE is None or _SEMAPHORE_LIMIT != limit:
        _SEMAPHORE = asyncio.Semaphore(limit)
        _SEMAPHORE_LIMIT = limit
    return _SEMAPHORE


def _flatten_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)
    return str(content)


def messages_to_prompt(messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> str:
    """Flatten chat messages into a single Claude CLI `-p` prompt."""
    blocks: list[str] = []
    for message in messages:
        role = str(message.get("role") or "user")
        text = _flatten_content(message.get("content"))
        if text:
            blocks.append(f"{role.upper()}:\n{text}")
    if tools:
        blocks.append("AVAILABLE_TOOLS:\n" + json.dumps(tools, ensure_ascii=False))
        blocks.append(
            "If you need a tool, reply with JSON "
            '{"tool_calls":[{"name":"tool","arguments":{}}]} and no other prose.'
        )
    return "\n\n".join(blocks).strip() or "(empty)"


def _looks_unauthenticated(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in _AUTH_MARKERS)


def _wire_model(model: str | None) -> str | None:
    if not model:
        return None
    stripped = model.strip()
    if not stripped or stripped == "auto":
        return None
    if "/" in stripped:
        prefix, rest = stripped.split("/", 1)
        if prefix.replace("-", "_").lower() in {"claude_code_cli", "claudecodecli"}:
            return rest or None
    return stripped


def parse_cli_json(payload: Any) -> LLMResponse:
    """Map Claude Code `--output-format json` (or a test double) to LLMResponse."""
    if isinstance(payload, str):
        text = payload.strip()
        if not text:
            return LLMResponse(content="", finish_reason="error", error_kind="empty")
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return LLMResponse(content=text, finish_reason="stop")

    if not isinstance(payload, dict):
        return LLMResponse(content=str(payload), finish_reason="stop")

    if payload.get("is_error") is True:
        detail = str(payload.get("result") or payload.get("error") or "Claude CLI returned an error")
        kind = "auth" if _looks_unauthenticated(detail) else "error"
        return LLMResponse(
            content=detail,
            finish_reason="error",
            error_kind=kind,
        )

    content = payload.get("result")
    if content is None:
        content = payload.get("content")
    if content is None:
        content = payload.get("text")
    text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)

    usage = _usage_from_payload(payload.get("usage"))
    return LLMResponse(
        content=text,
        finish_reason="stop",
        usage=usage,
    )


def _usage_from_payload(raw: Any) -> LLMUsage | None:
    if not isinstance(raw, dict):
        return None
    try:
        input_tokens = int(raw.get("input_tokens") or raw.get("prompt_tokens") or 0)
        output_tokens = int(raw.get("output_tokens") or raw.get("completion_tokens") or 0)
        cache_read = raw.get("cache_read_input_tokens") or raw.get("cache_read_tokens")
        cache_write = raw.get("cache_creation_input_tokens") or raw.get("cache_write_tokens")
        return LLMUsage.reported(
            input_tokens=max(0, input_tokens),
            output_tokens=max(0, output_tokens),
            cache_read_tokens=int(cache_read) if cache_read is not None else None,
            cache_write_tokens=int(cache_write) if cache_write is not None else None,
        )
    except (TypeError, ValueError):
        return None


class ClaudeCodeCliProvider(LLMProvider):
    """LLMProvider that invokes the local `claude` CLI instead of api.anthropic.com."""

    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None,
        default_model: str = "sonnet",
        *,
        provider_name: str = "claude_code_cli",
        timeout_s: float = _DEFAULT_TIMEOUT_S,
        max_concurrent: int = _DEFAULT_MAX_CONCURRENT,
        binary: str = _DEFAULT_BINARY,
        runner: Any | None = None,
    ):
        super().__init__(api_key, api_base, provider_name=provider_name)
        self.default_model = default_model
        self.timeout_s = float(timeout_s) if timeout_s else _DEFAULT_TIMEOUT_S
        self.max_concurrent = max(1, int(max_concurrent or _DEFAULT_MAX_CONCURRENT))
        self.binary = (binary or _DEFAULT_BINARY).strip() or _DEFAULT_BINARY
        self._runner = runner or _run_claude_cli

    def get_default_model(self) -> str:
        return self.default_model

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        reasoning_effort: str | None = None,
        tool_choice: str | dict[str, Any] | None = None,
    ) -> LLMResponse:
        _ = max_tokens, temperature, reasoning_effort, tool_choice
        prompt = messages_to_prompt(messages, tools)
        wire_model = _wire_model(model or self.default_model)
        async with _cli_semaphore(self.max_concurrent):
            try:
                return await self._runner(
                    binary=self.binary,
                    prompt=prompt,
                    model=wire_model,
                    timeout_s=self.timeout_s,
                )
            except FileNotFoundError:
                return LLMResponse(
                    content=(
                        f"Claude Code CLI binary {self.binary!r} was not found on PATH. "
                        "Install Claude Code and run `claude` once to log in "
                        "(personal subscription; no ANTHROPIC_API_KEY)."
                    ),
                    finish_reason="error",
                    error_kind="missing_cli",
                )
            except asyncio.TimeoutError:
                return LLMResponse(
                    content=f"Claude Code CLI timed out after {self.timeout_s:.0f}s.",
                    finish_reason="error",
                    error_kind="timeout",
                    error_should_retry=True,
                )
            except Exception as exc:
                logger.exception("Claude Code CLI provider failed")
                return self._error_response_from_exception(exc)


async def _run_claude_cli(
    *,
    binary: str,
    prompt: str,
    model: str | None,
    timeout_s: float,
) -> LLMResponse:
    if shutil.which(binary) is None and not os.path.isfile(binary):
        raise FileNotFoundError(binary)

    command = [binary, "-p", prompt, "--output-format", "json"]
    if model:
        command.extend(["--model", model])

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout_b, stderr_b = await asyncio.wait_for(process.communicate(), timeout=timeout_s)
    except asyncio.TimeoutError:
        process.kill()
        with suppress(Exception):
            await process.communicate()
        raise

    stdout = (stdout_b or b"").decode("utf-8", errors="replace")
    stderr = (stderr_b or b"").decode("utf-8", errors="replace")
    combined = f"{stdout}\n{stderr}"
    if process.returncode not in (0, None) and _looks_unauthenticated(combined):
        return LLMResponse(
            content=(
                "Claude Code CLI is installed but not authenticated. "
                "Run `claude` in a terminal and complete login. "
                "This provider does not use ANTHROPIC_API_KEY."
            ),
            finish_reason="error",
            error_kind="auth",
        )
    if process.returncode not in (0, None) and not stdout.strip():
        detail = stderr.strip() or f"claude exited with code {process.returncode}"
        kind = "auth" if _looks_unauthenticated(detail) else "error"
        return LLMResponse(content=detail, finish_reason="error", error_kind=kind)
    return parse_cli_json(stdout)
