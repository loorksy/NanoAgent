"""Measured context folding, task layers, display metadata, and tool reuse."""

from __future__ import annotations

import asyncio
import json
from typing import Any, cast

import pytest

from mokli.agent.context_governance import (
    ContextGovernor,
    fold_completed_candle_arguments,
    fold_prior_assistant_reasoning,
    fold_prior_subagent_announcements,
    fold_prior_tool_results,
)
from mokli.agent.context_layers import (
    layers_for_archived_history,
    layers_for_task,
    layers_for_transcript_boundary,
    provider_tool_names_for_layers,
)
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


def test_prior_tool_image_bytes_are_not_resent() -> None:
    payload = "A" * 20000
    url = f"data:image/png;base64,{payload}"
    label = "(Image fetched from: https://example.test/chart.png)"
    blocks: list[dict[str, Any]] = [
        {"type": "image_url", "image_url": {"url": url}, "_meta": {"path": "/tmp/chart.png"}},
        {"type": "text", "text": label},
    ]
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": "انظر إلى الصورة ثم السعر"},
        _assistant_with_tools("web_fetch"),
        {
            "role": "tool",
            "tool_call_id": "call_web_fetch",
            "name": "web_fetch",
            "content": blocks,
        },
        _assistant_with_tools("get_gold_quote"),
        _tool_message("get_gold_quote", "bid 2400"),
    ]
    before = estimate_prompt_tokens(messages, None)
    folded, referenced, saved = fold_prior_tool_results(messages)
    after = estimate_prompt_tokens(folded, None)
    folded_blocks = folded[2]["content"]
    assert referenced == 1
    assert saved > 10000
    assert after < before
    assert url not in str(folded_blocks)
    assert folded_blocks[1]["text"] == label
    assert "لن تُعاد" in folded_blocks[0]["text"]
    assert folded[-1]["content"] == "bid 2400"
    assert messages[2]["content"][0]["image_url"]["url"] == url
    print(f"TOKEN_IMAGE_FOLD before={before} after={after} saved_chars={saved}")

    current_only = messages[:3]
    kept, referenced_now, _saved_now = fold_prior_tool_results(current_only)
    assert referenced_now == 0
    assert kept[2]["content"][0]["image_url"]["url"] == url


def test_prior_assistant_reasoning_is_not_resent() -> None:
    thinking = "مستوى " * 2000
    kept = "التفكير الحالي يبقى"
    signature = "sig-current"
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": "حلل الذهب"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"id": "call_quote", "type": "function", "function": {"name": "get_gold_quote", "arguments": "{}"}}],
            "reasoning_content": thinking,
            "thinking_blocks": [{"type": "thinking", "thinking": thinking, "signature": "sig-old"}],
        },
        _tool_message("get_gold_quote", "bid 2400"),
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"id": "call_kernel", "type": "function", "function": {"name": "run_trading_kernel", "arguments": "{}"}}],
            "reasoning_content": kept,
            "thinking_blocks": [{"type": "thinking", "thinking": kept, "signature": signature}],
        },
        _tool_message("run_trading_kernel", "wait"),
    ]
    before = estimate_prompt_tokens(messages, None)
    folded, count, saved = fold_prior_assistant_reasoning(messages)
    after = estimate_prompt_tokens(folded, None)
    assert count == 1
    assert saved > 5000
    assert after < before
    assert folded[1]["reasoning_content"].startswith("[تفكير دورة سابقة:")
    assert "thinking_blocks" not in folded[1]
    assert thinking not in folded[1]["reasoning_content"]
    assert folded[3]["reasoning_content"] == kept
    assert folded[3]["thinking_blocks"][0]["signature"] == signature
    assert messages[1]["reasoning_content"] == thinking
    assert messages[1]["thinking_blocks"][0]["signature"] == "sig-old"
    print(f"TOKEN_REASONING before={before} after={after} saved_chars={saved}")

    finished: list[dict[str, Any]] = [
        {"role": "user", "content": "سؤال"},
        {
            "role": "assistant",
            "content": "جواب",
            "reasoning_content": thinking,
            "thinking_blocks": [{"type": "thinking", "thinking": thinking, "signature": "sig"}],
        },
        {"role": "user", "content": "التالي"},
    ]
    folded_next, count_next, _saved_next = fold_prior_assistant_reasoning(finished)
    assert count_next == 1
    assert "thinking_blocks" not in folded_next[1]
    assert finished[1]["thinking_blocks"][0]["signature"] == "sig"


def _subagent_announce(label: str, task: str, result: str) -> str:
    return (
        f"[Subagent '{label}' completed successfully]\n\n"
        f"Task: {task}\n\n"
        f"Result:\n{result}\n\n"
        "Summarize this naturally for the user. Keep it brief (1-2 sentences). "
        'Do not mention technical details like "subagent" or task IDs.'
    )


def test_finished_subagent_announcement_is_not_resent() -> None:
    task = "TASK_BODY_MARKER ابحث عن محرك الذهب " + ("تفصيل " * 400)
    result = "RESULT_BODY_MARKER " + ("خلاصة " * 800)
    announce = _subagent_announce("research", task, result)
    assert len(announce) > 1200
    older = _subagent_announce("older", "مهمة قديمة " + ("سطر " * 400), "نتيجة قديمة " + ("سطر " * 400))
    short = _subagent_announce("brief", "مهمة قصيرة", "تم")
    assert len(short) <= 1200
    follow_up = "لخّص ذلك بجملة"
    current_user_copy = _subagent_announce("live", task, result)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "ابحث"},
        {"role": "assistant", "content": older},
        {"role": "user", "content": "ثم؟"},
        {"role": "assistant", "content": announce},
        {"role": "assistant", "content": short},
        {"role": "user", "content": follow_up},
        {"role": "user", "content": current_user_copy},
    ]
    before = estimate_prompt_tokens(messages, None)
    folded, referenced, saved = fold_prior_subagent_announcements(messages)
    after = estimate_prompt_tokens(folded, None)
    assert referenced == 2
    assert saved > 1000
    assert after < before
    assert folded[2]["content"].startswith("[مرجع نتيجة وكيل سابق:")
    assert "TASK_BODY_MARKER" not in folded[2]["content"]
    assert folded[4]["content"].startswith("[مرجع نتيجة وكيل سابق:")
    assert "[Subagent 'research' completed successfully]" in folded[4]["content"]
    assert "RESULT_BODY_MARKER" not in folded[4]["content"]
    assert folded[5]["content"] == short
    assert folded[-1]["content"] == current_user_copy
    assert folded[-2]["content"] == follow_up
    assert messages[2]["content"] == older
    assert messages[4]["content"] == announce
    print(f"TOKEN_ANNOUNCE before={before} after={after} saved_chars={saved}")

    next_turn = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "ابحث"},
        {"role": "assistant", "content": announce},
        {"role": "user", "content": "وما بعد؟"},
    ]
    before_next = estimate_prompt_tokens(next_turn, None)
    folded_next, referenced_next, saved_next = fold_prior_subagent_announcements(next_turn)
    after_next = estimate_prompt_tokens(folded_next, None)
    assert referenced_next == 1
    assert saved_next > 1000
    assert after_next < before_next
    assert folded_next[2]["content"].startswith("[مرجع نتيجة وكيل سابق:")
    assert "RESULT_BODY_MARKER" not in folded_next[2]["content"]
    assert next_turn[2]["content"] == announce
    print(
        f"TOKEN_ANNOUNCE_NEXT before={before_next} after={after_next} "
        f"saved_chars={saved_next}"
    )

    unread = [
        {"role": "user", "content": "ابحث"},
        {"role": "assistant", "content": older},
        {"role": "assistant", "content": announce},
    ]
    kept, referenced_now, _saved_now = fold_prior_subagent_announcements(unread)
    assert referenced_now == 1
    assert kept[-1]["content"] == announce
    assert "RESULT_BODY_MARKER" not in kept[1]["content"]
    assert unread[1]["content"] == older


def test_subagent_announcement_fold_is_recorded() -> None:
    from mokli.agent.turn_diagnostics import (
        TurnDiagnostics,
        bind_turn_diagnostics,
        reset_turn_diagnostics,
    )

    announce = _subagent_announce("research", "مهمة " * 400, "نتيجة " * 400)
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": "ابحث"},
        {"role": "assistant", "content": announce},
        {"role": "user", "content": "وما بعد؟"},
    ]
    diag = TurnDiagnostics(model="test", provider="Test")
    token = bind_turn_diagnostics(diag)
    try:
        folded = ContextGovernor().apply_tool_result_budget(cast(Any, object()), messages)
    finally:
        reset_turn_diagnostics(token)
    assert folded[1]["content"].startswith("[مرجع نتيجة وكيل سابق:")
    assert messages[1]["content"] == announce
    assert diag.folded_subagent_announcements == 1
    assert diag.folded_subagent_chars > 1000
    payload = diag.to_dict()
    assert payload["folded_subagent_announcements"] == 1
    assert payload["folded_subagent_chars"] == diag.folded_subagent_chars


def _candle_rows(count: int) -> list[dict[str, float | int]]:
    rows: list[dict[str, float | int]] = []
    price = 2300.0
    for index in range(count):
        price += 1.2
        rows.append(
            {
                "time_ms": index * 60_000,
                "open": round(price - 0.2, 4),
                "high": round(price + 0.3, 4),
                "low": round(price - 0.4, 4),
                "close": round(price, 4),
            }
        )
    return rows


def test_completed_candle_arguments_are_not_resent() -> None:
    pasted = json.dumps(_candle_rows(200), ensure_ascii=False)
    assert len(pasted) > 1200
    arguments = json.dumps(
        {"description": "كسر قمة الساعة", "candles_json": pasted},
        ensure_ascii=False,
    )
    call = {
        "id": "call_replay",
        "type": "function",
        "function": {"name": "fast_backtest", "arguments": arguments},
    }
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": "اختبر الخوارزمية"},
        {"role": "assistant", "content": "", "tool_calls": [call]},
        {
            "role": "tool",
            "tool_call_id": "call_replay",
            "name": "fast_backtest",
            "content": '{"ok": true, "trades": 3}',
        },
    ]
    before = estimate_prompt_tokens(messages, None)
    folded, count, saved = fold_completed_candle_arguments(messages)
    after = estimate_prompt_tokens(folded, None)
    rewritten = folded[1]["tool_calls"][0]["function"]["arguments"]
    parsed = json.loads(rewritten)
    assert count == 1
    assert saved > 1000
    assert after < before
    assert parsed["description"] == "كسر قمة الساعة"
    assert parsed["candles_json"].startswith("[مرجع شموع سابقة:")
    assert pasted not in rewritten
    assert messages[1]["tool_calls"][0]["function"]["arguments"] == arguments
    print(f"TOKEN_CANDLE_ARGS before={before} after={after} saved_chars={saved}")

    pending = messages[:2]
    kept, pending_count, _pending_saved = fold_completed_candle_arguments(pending)
    assert pending_count == 0
    assert kept[1]["tool_calls"][0]["function"]["arguments"] == arguments

    short = json.dumps({"candles_json": "[]"}, ensure_ascii=False)
    short_messages: list[dict[str, Any]] = [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_short",
                    "type": "function",
                    "function": {"name": "fast_backtest", "arguments": short},
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_short",
            "name": "fast_backtest",
            "content": "{}",
        },
    ]
    unchanged, short_count, _short_saved = fold_completed_candle_arguments(short_messages)
    assert short_count == 0
    assert unchanged[0]["tool_calls"][0]["function"]["arguments"] == short


def test_candle_argument_fold_is_recorded_on_the_turn() -> None:
    from types import SimpleNamespace

    from mokli.agent.context_governance import ContextGovernor
    from mokli.agent.turn_diagnostics import (
        TurnDiagnostics,
        bind_turn_diagnostics,
        reset_turn_diagnostics,
    )

    pasted = json.dumps(_candle_rows(200), ensure_ascii=False)
    arguments = json.dumps({"candles_json": pasted}, ensure_ascii=False)
    messages: list[dict[str, Any]] = [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_replay",
                    "type": "function",
                    "function": {"name": "fast_backtest", "arguments": arguments},
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_replay",
            "name": "fast_backtest",
            "content": '{"ok": true}',
        },
    ]
    diag = TurnDiagnostics(model="test", provider="Test")
    token = bind_turn_diagnostics(diag)
    try:
        prepared = ContextGovernor().apply_tool_result_budget(
            SimpleNamespace(workspace=None, session_key=None, max_tool_result_chars=16_000),  # type: ignore[arg-type]
            messages,
        )
    finally:
        reset_turn_diagnostics(token)
    payload = diag.to_dict()
    assert payload["folded_candle_arguments"] == 1
    assert payload["folded_candle_chars"] > 1000
    assert pasted not in prepared[0]["tool_calls"][0]["function"]["arguments"]
    assert messages[0]["tool_calls"][0]["function"]["arguments"] == arguments


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


def test_light_turn_defers_trading_tool_schemas() -> None:
    registered = [
        "message",
        "web_search",
        "web_fetch",
        "read_file",
        "list_dir",
        "get_gold_quote",
        "run_trading_kernel",
    ]
    light = provider_tool_names_for_layers(registered, layers_for_task("مرحبا"))
    assert light == ["message", "web_search", "web_fetch"]
    full = provider_tool_names_for_layers(registered, layers_for_task("حلل الذهب"))
    assert full == registered


def test_registry_definitions_for_names_subset() -> None:
    class _NamedTool(Tool):
        def __init__(self, tool_name: str) -> None:
            self._name = tool_name

        @property
        def name(self) -> str:
            return self._name

        @property
        def description(self) -> str:
            return "x"

        @property
        def parameters(self) -> dict[str, Any]:
            return {"type": "object", "properties": {}}

        async def execute(self, **kwargs: Any) -> str:
            return "ok"

    registry = ToolRegistry()
    registry.register(_NamedTool("alpha"))
    registry.register(_NamedTool("beta"))
    names = registry.get_definitions_for_names(["beta"])
    assert len(names) == 1
    assert names[0]["function"]["name"] == "beta"


def test_short_turn_system_prompt_uses_compact_tool_contracts(tmp_path) -> None:
    from mokli.agent.context import ContextBuilder, TranscriptInput

    tool_names = ["get_gold_quote", "message", "run_trading_kernel"]
    builder = ContextBuilder(tmp_path)
    full_messages = builder.build_transcript(
        TranscriptInput(history=[], current_message="حلل الذهب"),
        tool_names=tool_names,
    )
    short_messages = builder.build_transcript(
        TranscriptInput(history=[], current_message="مرحبا"),
        tool_names=tool_names,
    )
    full_sys = full_messages[0]["content"]
    short_sys = short_messages[0]["content"]
    assert "Teams and debate" in full_sys
    assert "Teams and debate" not in short_sys
    assert "Execution permission levels" in short_sys
    full_tok = estimate_prompt_tokens(full_messages, None)
    short_tok = estimate_prompt_tokens(short_messages, None)
    assert short_tok < full_tok - 150


def test_archive_layers_follow_last_user_turn() -> None:
    history = [
        {"role": "user", "content": "مرحبا"},
        {"role": "assistant", "content": "أهلاً"},
    ]
    layers = layers_for_archived_history(history)
    assert layers.include_memory is False
    assert layers.include_skills is False


def test_compaction_summary_layers_follow_turn_not_empty_tail() -> None:
    history = [{"role": "user", "content": "مرحبا"}]
    turn_layers = layers_for_transcript_boundary(
        current_message="كيف الحال",
        history=history,
    )
    summary_layers = layers_for_transcript_boundary(
        current_message=None,
        history=[],
        prompt_layers=turn_layers,
    )
    assert summary_layers.include_memory is False
    assert summary_layers.include_skills is False
    empty_tail = layers_for_transcript_boundary(current_message=None, history=[])
    assert empty_tail.include_memory is True
    assert empty_tail.include_skills is True


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
    assert payload["nested_calls"] == [
        {
            "label": "",
            "input_tokens": 800,
            "output_tokens": 40,
            "system_tokens": 0,
            "user_tokens": 0,
            "other_tokens": 0,
            "estimated": False,
        },
        {
            "label": "",
            "input_tokens": 120,
            "output_tokens": 10,
            "system_tokens": 0,
            "user_tokens": 0,
            "other_tokens": 0,
            "estimated": True,
        },
    ]


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
    call = diag.nested_calls[0]
    assert call["label"] == "Risk Officer"
    assert call["input_tokens"] == 640
    assert call["system_tokens"] > 0
    assert call["user_tokens"] > 0
    assert call["estimated"] is False


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
    payload = diag.to_dict()
    assert payload["nested_usage"] == "estimated"
    assert payload["nested_calls"][0]["label"] == "synthesizer"
    assert payload["nested_calls"][0]["user_tokens"] > 0
    assert payload["nested_calls"][0]["system_tokens"] == 0


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
    assert payload["provider_tool_count"] == 0


def test_note_prepared_records_provider_tool_count() -> None:
    from mokli.agent.turn_diagnostics import TurnDiagnostics

    diag = TurnDiagnostics(model="test", provider="Test")
    diag.note_prepared(
        [{"role": "system", "content": "x"}, {"role": "user", "content": "hi"}],
        [{"type": "function", "function": {"name": "a", "description": "d", "parameters": {}}}],
    )
    assert diag.provider_tool_count == 1
    assert diag.to_dict()["provider_tool_count"] == 1


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
