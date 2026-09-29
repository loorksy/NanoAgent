"""Per-turn measurements for developers. Hidden from the normal chat status."""

from __future__ import annotations

import time
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Any

from mokli.providers.base import LLMUsage
from mokli.utils.helpers import estimate_message_tokens, estimate_prompt_tokens

# Illustrative rates so a developer can compare turns. Not an invoice.
_INPUT_USD_PER_MILLION = 3.0
_OUTPUT_USD_PER_MILLION = 15.0
_SUBAGENT_RESULT_TOOLS = frozenset({"spawn", "run_trading_team", "trading_team"})

_CURRENT: ContextVar[TurnDiagnostics | None] = ContextVar(
    "mokli_turn_diagnostics",
    default=None,
)
_LATEST: dict[str, dict[str, Any]] = {}


def current_turn_diagnostics() -> TurnDiagnostics | None:
    return _CURRENT.get()


def bind_turn_diagnostics(diag: TurnDiagnostics) -> Token[TurnDiagnostics | None]:
    return _CURRENT.set(diag)


def reset_turn_diagnostics(token: Token[TurnDiagnostics | None]) -> None:
    _CURRENT.reset(token)


def remember_diagnostics(session_key: str | None, payload: dict[str, Any]) -> None:
    if session_key:
        _LATEST[session_key] = payload


def latest_diagnostics(session_key: str | None) -> dict[str, Any] | None:
    if not session_key:
        return None
    return _LATEST.get(session_key)


def _text_len(content: Any) -> int:
    if isinstance(content, str):
        return len(content)
    if isinstance(content, list):
        return sum(_text_len(item.get("text") if isinstance(item, dict) else item) for item in content)
    if content is None:
        return 0
    return len(str(content))


def component_tokens(messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None) -> dict[str, int]:
    """Estimate tokens by role. Tool definitions are counted once for this payload."""
    system = 0
    conversation = 0
    tool_results = 0
    subagent = 0
    other = 0
    for message in messages:
        tokens = estimate_message_tokens(message)
        role = message.get("role")
        if role == "system":
            system += tokens
        elif role == "tool" and str(message.get("name") or "") in _SUBAGENT_RESULT_TOOLS:
            subagent += tokens
        elif role == "tool":
            tool_results += tokens
        elif role in {"user", "assistant"}:
            conversation += tokens
        else:
            other += tokens
    tool_definitions = estimate_prompt_tokens([], tools) if tools else 0
    return {
        "system": system,
        "conversation": conversation,
        "tool_definitions": tool_definitions,
        "tool_results": tool_results,
        "subagent": subagent,
        "other": other,
        "final": system + conversation + tool_results + subagent + other + tool_definitions,
    }


@dataclass
class TurnDiagnostics:
    model: str
    provider: str
    started_at: float = field(default_factory=time.perf_counter)
    context_ms: int = 0
    model_ms: int = 0
    tool_ms: int = 0
    retry_ms: int = 0
    _retry_ms_this_round: int = 0
    rounds: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: int = 0
    reused_tool_calls: int = 0
    referenced_tool_results: int = 0
    referenced_chars_saved: int = 0
    tool_result_chars: list[dict[str, Any]] = field(default_factory=list)
    components: dict[str, int] = field(default_factory=dict)
    memory_chars: int = 0
    skills_chars: int = 0
    memory_tokens: int = 0
    skills_tokens: int = 0
    static_resends: int = 0
    _system_fingerprint: str = ""

    def note_context(self, elapsed_ms: int) -> None:
        """Record context-build time. Memory sizes are set while the prompt is built."""
        self.context_ms += max(0, elapsed_ms)

    def note_prepared(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
    ) -> None:
        components = component_tokens(messages, tools)
        components["memory"] = self.memory_tokens
        components["skills"] = self.skills_tokens
        self.components = components
        system = next((m.get("content") for m in messages if m.get("role") == "system"), "")
        fingerprint = system if isinstance(system, str) else str(system)
        if self._system_fingerprint and fingerprint == self._system_fingerprint:
            self.static_resends += 1
        elif fingerprint:
            self._system_fingerprint = fingerprint

    def note_retry_wait(self, elapsed_ms: int) -> None:
        """Record provider retry sleep separately from model generation time."""
        waited = max(0, elapsed_ms)
        self.retry_ms += waited
        self._retry_ms_this_round += waited

    def note_model_round(self, elapsed_ms: int, usage: LLMUsage | None) -> None:
        self.rounds += 1
        waited = self._retry_ms_this_round
        self._retry_ms_this_round = 0
        self.model_ms += max(0, elapsed_ms - waited)
        if usage is None:
            return
        self.input_tokens += usage.input_tokens
        self.output_tokens += usage.output_tokens

    def note_tool_batch(
        self,
        elapsed_ms: int,
        events: list[dict[str, str]],
        results: list[Any],
    ) -> None:
        self.tool_ms += max(0, elapsed_ms)
        for event, result in zip(events, results):
            name = str(event.get("name") or "")
            status = str(event.get("status") or "")
            size = _text_len(result)
            self.tool_calls += 1
            if status == "reused":
                self.reused_tool_calls += 1
            self.tool_result_chars.append({"name": name, "chars": size, "status": status})

    def note_references(self, count: int, chars_saved: int) -> None:
        self.referenced_tool_results += count
        self.referenced_chars_saved += chars_saved

    def to_dict(self) -> dict[str, Any]:
        elapsed_ms = int((time.perf_counter() - self.started_at) * 1000)
        input_cost = self.input_tokens / 1_000_000 * _INPUT_USD_PER_MILLION
        output_cost = self.output_tokens / 1_000_000 * _OUTPUT_USD_PER_MILLION
        return {
            "model": self.model,
            "provider": self.provider,
            "elapsed_ms": elapsed_ms,
            "context_ms": self.context_ms,
            "model_ms": self.model_ms,
            "tool_ms": self.tool_ms,
            "retry_ms": self.retry_ms,
            "rounds": self.rounds,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.input_tokens + self.output_tokens,
            "tool_calls": self.tool_calls,
            "reused_tool_calls": self.reused_tool_calls,
            "referenced_tool_results": self.referenced_tool_results,
            "referenced_chars_saved": self.referenced_chars_saved,
            "tool_result_chars": list(self.tool_result_chars),
            "components": dict(self.components),
            "memory_chars": self.memory_chars,
            "skills_chars": self.skills_chars,
            "memory_tokens": self.memory_tokens,
            "skills_tokens": self.skills_tokens,
            "static_resends": self.static_resends,
            "cost_estimate_usd": round(input_cost + output_cost, 6),
            "cost_rate_note": (
                f"illustrative ${_INPUT_USD_PER_MILLION}/M input and "
                f"${_OUTPUT_USD_PER_MILLION}/M output, not an invoice"
            ),
            "component_note": "memory and skills are inside system and are not added again to final",
        }
