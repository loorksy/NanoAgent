"""Measured context folding, task layers, display metadata, and tool reuse."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from mokli.agent.context_governance import fold_prior_tool_results
from mokli.agent.context_layers import layers_for_task
from mokli.agent.hook import AgentHook
from mokli.agent.tools.base import Tool
from mokli.agent.tools.context import ToolContext
from mokli.agent.tools.display import DISPLAY, phrase_for
from mokli.agent.tools.execution import execute_tool_calls
from mokli.agent.tools.loader import ToolLoader
from mokli.agent.tools.registry import ToolRegistry
from mokli.config.schema import ToolsConfig
from mokli.providers.base import ToolCallRequest
from mokli.trading.teams.runtime import load_preset, topological_layers
from mokli.utils.helpers import estimate_prompt_tokens


def _assistant_with_tools(*names: str) -> dict[str, Any]:
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": f"call_{name}",
                "type": "function",
                "function": {"name": name, "arguments": "{}"},
            }
            for name in names
        ],
    }


def _tool_message(name: str, content: str) -> dict[str, Any]:
    return {
        "role": "tool",
        "tool_call_id": f"call_{name}",
        "name": name,
        "content": content,
    }


def test_prior_tool_results_are_referenced_instead_of_resent() -> None:
    bulky = "سعر " * 2000
    assert len(bulky) > 1200
    latest = "النتيجة الأخيرة " + ("x" * 2000)
    messages = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "حلل الذهب"},
        _assistant_with_tools("get_gold_quote"),
        _tool_message("get_gold_quote", bulky),
        _assistant_with_tools("run_trading_kernel"),
        _tool_message("run_trading_kernel", latest),
    ]
    before = estimate_prompt_tokens(messages, None)
    folded, referenced, saved = fold_prior_tool_results(messages)
    after = estimate_prompt_tokens(folded, None)
    assert referenced == 1
    assert saved > 1000
    assert after < before
    assert folded[-1]["content"] == latest
    assert folded[3]["content"].startswith("[مرجع نتيجة سابقة:")
    assert "get_gold_quote" in folded[3]["content"]
    assert bulky not in folded[3]["content"]
    print(f"TOKEN_FOLD before={before} after={after} saved_chars={saved}")


def test_finished_turn_tool_result_is_not_resent_on_the_next_question() -> None:
    bulky = "سعر " * 2000
    follow_up = "وما الوقف؟"
    messages = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "حلل الذهب"},
        _assistant_with_tools("run_trading_kernel"),
        _tool_message("run_trading_kernel", bulky),
        {"role": "assistant", "content": "الانتظار أنسب الآن."},
        {"role": "user", "content": follow_up},
    ]
    before = estimate_prompt_tokens(messages, None)
    folded, referenced, saved = fold_prior_tool_results(messages)
    after = estimate_prompt_tokens(folded, None)
    assert referenced == 1
    assert saved > 1000
    assert after < before
    assert folded[-1]["content"] == follow_up
    assert folded[3]["content"].startswith("[مرجع نتيجة سابقة:")
    assert bulky not in folded[3]["content"]
    assert messages[3]["content"] == bulky
    print(f"TOKEN_NEXT_TURN before={before} after={after} saved_chars={saved}")

    current = "القرار الحالي " + ("z" * 2000)
    continued = [
        *messages,
        _assistant_with_tools("get_gold_quote"),
        _tool_message("get_gold_quote", current),
    ]
    folded_now, referenced_now, _saved_now = fold_prior_tool_results(continued)
    assert referenced_now == 1
    assert bulky not in folded_now[3]["content"]
    assert folded_now[-1]["content"] == current


def test_latest_tool_batch_stays_complete() -> None:
    bulky = "y" * 3000
    messages = [
        {"role": "user", "content": "سؤال"},
        _assistant_with_tools("fetch_evidence"),
        _tool_message("fetch_evidence", bulky),
    ]
    folded, referenced, _saved = fold_prior_tool_results(messages)
    assert referenced == 0
    assert folded[-1]["content"] == bulky


def test_decision_review_runs_technical_before_review() -> None:
    preset = load_preset("gold_decision_review")
    layers = [[task.id for task in layer] for layer in topological_layers(preset.tasks)]
    assert layers[0] == ["task-technical"]
    assert "task-review" in layers[-1]
    assert layers.index(["task-technical"]) < layers.index(["task-review"])


def test_short_question_skips_memory_and_skills() -> None:
    plain = layers_for_task("مرحبا")
    assert plain.include_memory is False
    assert plain.include_skills is False
    trading = layers_for_task("هل أشتري الذهب؟")
    assert trading.include_memory is True
    assert trading.include_skills is True


def test_registered_tools_have_display_copy() -> None:
    registry = ToolRegistry()
    ToolLoader().load(ToolContext(config=ToolsConfig(), workspace="/tmp"), registry)
    missing = [name for name in registry.tool_names if name not in DISPLAY]
    assert missing == []
    assert phrase_for("get_gold_quote", "started") == "يفحص سعر الذهب الحالي…"
    assert phrase_for("get_gate_report", "finished") == "اكتمل فحص شروط القرار"
    assert phrase_for("run_trading_kernel", "started") == "يشغّل محرك التحليل"
    assert "get_gold_quote" not in phrase_for("get_gold_quote", "started")


class _Quote(Tool):
    def __init__(self) -> None:
        self.calls = 0

    @property
    def name(self) -> str:
        return "get_gold_quote"

    @property
    def description(self) -> str:
        return "quote"

    @property
    def parameters(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    @property
    def read_only(self) -> bool:
        return True

    async def execute(self, **kwargs: Any) -> str:
        self.calls += 1
        return "bid 2400"


@pytest.mark.asyncio
async def test_read_only_tool_is_not_executed_twice_in_one_turn() -> None:
    tool = _Quote()
    registry = ToolRegistry()
    registry.register(tool)
    hook = AgentHook()
    cache: dict[str, Any] = {}
    call = ToolCallRequest(id="c1", name="get_gold_quote", arguments={})
    first, events = await execute_tool_calls(
        registry,
        [call],
        concurrent=False,
        external_lookup_counts={},
        workspace_violation_counts={},
        hook=hook,
        context=None,  # type: ignore[arg-type]
        result_cache=cache,
    )
    second_call = ToolCallRequest(id="c2", name="get_gold_quote", arguments={})
    second, second_events = await execute_tool_calls(
        registry,
        [second_call],
        concurrent=False,
        external_lookup_counts={},
        workspace_violation_counts={},
        hook=hook,
        context=None,  # type: ignore[arg-type]
        result_cache=cache,
    )
    assert tool.calls == 1
    assert events[0]["status"] == "ok"
    assert second_events[0]["status"] == "reused"
    assert "لم تُعد الأداة" in str(second[0])
    assert first[0] == "bid 2400"


def test_retry_wait_is_not_counted_as_model_time() -> None:
    from mokli.agent.turn_diagnostics import TurnDiagnostics

    diag = TurnDiagnostics(model="test", provider="Test")
    diag.note_retry_wait(1800)
    diag.note_model_round(2500, None)
    assert diag.retry_ms == 1800
    assert diag.model_ms == 700
    payload = diag.to_dict()
    assert payload["retry_ms"] == 1800
    assert payload["model_ms"] == 700


@pytest.mark.asyncio
async def test_provider_retry_sleep_is_recorded() -> None:
    from mokli.agent.turn_diagnostics import (
        TurnDiagnostics,
        bind_turn_diagnostics,
        reset_turn_diagnostics,
    )
    from mokli.providers.base import LLMProvider

    class _Provider(LLMProvider):
        def get_default_model(self) -> str:
            return "test"

        async def chat(self, *args: object, **kwargs: object) -> object:
            del args, kwargs
            return None

        async def _wait_retry(self, *args: object, **kwargs: object) -> None:
            del args, kwargs
            await asyncio.sleep(0.05)

    diag = TurnDiagnostics(model="test", provider="Test")
    token = bind_turn_diagnostics(diag)
    try:
        await _Provider(provider_name="test")._sleep_with_heartbeat(
            0.05,
            attempt=1,
            persistent=False,
            error_kind="rate_limit",
            max_attempts=3,
        )
    finally:
        reset_turn_diagnostics(token)
    assert diag.retry_ms >= 40


def test_nested_model_calls_are_not_parent_rounds() -> None:
    from mokli.agent.turn_diagnostics import TurnDiagnostics

    diag = TurnDiagnostics(model="test", provider="Test")
    diag.note_model_round(900, None)
    diag.note_nested_model(1400, input_tokens=800, output_tokens=40, estimated=False)
    diag.note_nested_model(300, input_tokens=120, output_tokens=10, estimated=True)
    assert diag.model_ms == 900
    assert diag.rounds == 1
    assert diag.input_tokens == 0
    payload = diag.to_dict()
    assert payload["nested_rounds"] == 2
    assert payload["nested_model_ms"] == 1700
    assert payload["nested_input_tokens"] == 920
    assert payload["nested_output_tokens"] == 50
    assert payload["request_input_tokens"] == 920
    assert payload["total_tokens"] == 970
    assert payload["nested_usage"] == "mixed"
    assert payload["components"]["nested_model"] == 970
    assert payload["cost_estimate_usd"] > 0


@pytest.mark.asyncio
async def test_team_role_usage_is_recorded_on_the_turn() -> None:
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock

    from mokli.agent.tools.context import RequestContext, request_context
    from mokli.agent.turn_diagnostics import (
        TurnDiagnostics,
        bind_turn_diagnostics,
        reset_turn_diagnostics,
    )
    from mokli.providers.base import LLMUsage
    from mokli.trading.teams.subagent_runner import run_team_role
    from mokli.utils.llm_runtime import LLMRuntime

    provider = MagicMock()
    provider.chat = AsyncMock(
        return_value=SimpleNamespace(
            content="STANCE: wait",
            usage=LLMUsage.reported(input_tokens=640, output_tokens=18),
        )
    )
    runtime = LLMRuntime.capture(provider, "test-model", context_window_tokens=128_000)
    diag = TurnDiagnostics(model="test-model", provider="Test")
    token = bind_turn_diagnostics(diag)
    try:
        with request_context(RequestContext(channel="agent_api", chat_id="chat", runtime=runtime)):
            summary = await run_team_role(
                agent_id="risk",
                role="Risk Officer",
                task_text="Name blocking risks.",
                evidence_text='{"last_close": 2300}',
                system_prompt="role:risk",
            )
    finally:
        reset_turn_diagnostics(token)
    assert summary.startswith("STANCE: wait")
    assert diag.rounds == 0
    assert diag.model_ms == 0
    assert diag.nested_rounds == 1
    assert diag.nested_input_tokens == 640
    assert diag.nested_output_tokens == 18
    assert diag.nested_estimated_rounds == 0


@pytest.mark.asyncio
async def test_synthesizer_call_without_usage_is_estimated() -> None:
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock

    from mokli.agent.tools.context import RequestContext, request_context
    from mokli.agent.turn_diagnostics import (
        TurnDiagnostics,
        bind_turn_diagnostics,
        reset_turn_diagnostics,
    )
    from mokli.trading.agents.synthesizer import _runtime_complete
    from mokli.utils.llm_runtime import LLMRuntime

    provider = MagicMock()
    provider.generation = SimpleNamespace(max_tokens=512)
    provider.chat = AsyncMock(return_value=SimpleNamespace(content='{"decision":"wait"}', usage=None))
    runtime = LLMRuntime.capture(provider, "test-model", context_window_tokens=128_000)
    diag = TurnDiagnostics(model="test-model", provider="Test")
    token = bind_turn_diagnostics(diag)
    messages = [{"role": "user", "content": "FROZEN EVIDENCE"}]
    try:
        with request_context(RequestContext(channel="agent_api", chat_id="chat", runtime=runtime)):
            text = await _runtime_complete(messages)
    finally:
        reset_turn_diagnostics(token)
    assert text == '{"decision":"wait"}'
    assert diag.input_tokens == 0
    assert diag.nested_rounds == 1
    assert diag.nested_estimated_rounds == 1
    assert diag.nested_input_tokens > 0
    assert diag.nested_output_tokens > 0
    assert diag.to_dict()["nested_usage"] == "estimated"


def test_context_timing_keeps_memory_measured_during_prompt_build(tmp_path) -> None:
    from mokli.agent.context import ContextBuilder
    from mokli.agent.turn_diagnostics import (
        TurnDiagnostics,
        bind_turn_diagnostics,
        reset_turn_diagnostics,
    )

    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    (memory_dir / "MEMORY.md").write_text("The operator trades XAUUSD from Dubai.\n", encoding="utf-8")
    diag = TurnDiagnostics(model="test", provider="Test")
    token = bind_turn_diagnostics(diag)
    try:
        ContextBuilder(workspace=tmp_path).build_system_prompt()
        diag.note_context(12)
        diag.note_prepared(
            [{"role": "system", "content": "identity"}, {"role": "user", "content": "hi"}],
            None,
        )
    finally:
        reset_turn_diagnostics(token)
    assert diag.context_ms == 12
    assert diag.memory_chars > 0
    assert diag.memory_tokens > 0
    payload = diag.to_dict()
    assert payload["memory_tokens"] == diag.memory_tokens
    assert payload["components"]["memory"] == diag.memory_tokens
    assert payload["components"]["final"] == (
        payload["components"]["system"]
        + payload["components"]["conversation"]
        + payload["components"]["tool_results"]
        + payload["components"]["subagent"]
        + payload["components"]["other"]
        + payload["components"]["tool_definitions"]
    )


def test_component_tokens_count_subagent_results_apart_from_tools() -> None:
    from mokli.agent.turn_diagnostics import component_tokens

    parts = component_tokens(
        [
            {"role": "system", "content": "identity"},
            {"role": "user", "content": "hello"},
            {"role": "tool", "name": "get_gold_quote", "content": "2300"},
            {"role": "tool", "name": "spawn", "content": "Risk Officer says wait for the level."},
        ],
        None,
    )
    assert parts["subagent"] > 0
    assert parts["tool_results"] > 0
    assert parts["subagent"] != parts["tool_results"]
    assert parts["final"] == (
        parts["system"] + parts["conversation"] + parts["tool_results"]
        + parts["subagent"] + parts["other"] + parts["tool_definitions"]
    )
