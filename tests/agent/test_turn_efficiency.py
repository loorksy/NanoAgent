"""Measured context folding, task layers, display metadata, and tool reuse."""

from __future__ import annotations

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
