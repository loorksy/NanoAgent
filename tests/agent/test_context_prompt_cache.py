"""Tests for cache-friendly prompt construction."""

from __future__ import annotations

import datetime as datetime_module
from datetime import datetime as real_datetime
from importlib.resources import files as pkg_files
from pathlib import Path

import pytest

from mokli.agent.context import ContextBuilder
from mokli.runtime_context import RuntimeContextBlock


class _FakeDatetime(real_datetime):
    current = real_datetime(2026, 2, 24, 13, 59)

    @classmethod
    def now(cls, tz=None):  # type: ignore[override]
        return cls.current


def _make_workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True)
    return workspace


def test_bootstrap_files_are_backed_by_templates() -> None:
    template_dir = pkg_files("mokli") / "templates"

    for filename in ContextBuilder.BOOTSTRAP_FILES:
        assert (template_dir / filename).is_file(), f"missing bootstrap template: {filename}"


def test_system_prompt_stays_stable_when_clock_changes(tmp_path, monkeypatch) -> None:
    """System prompt should not change just because wall clock minute changes."""
    monkeypatch.setattr(datetime_module, "datetime", _FakeDatetime)

    workspace = _make_workspace(tmp_path)
    builder = ContextBuilder(workspace)

    _FakeDatetime.current = real_datetime(2026, 2, 24, 13, 59)
    prompt1 = builder.build_system_prompt()

    _FakeDatetime.current = real_datetime(2026, 2, 24, 14, 0)
    prompt2 = builder.build_system_prompt()

    assert prompt1 == prompt2


def test_selected_project_path_follows_shared_cache_prefix(tmp_path) -> None:
    """Project paths must not invalidate the stable identity and tool contract prefix."""
    agent_home = tmp_path / "agent-home"
    project_a = tmp_path / "project-a"
    project_b = tmp_path / "project-b"
    agent_home.mkdir()
    project_a.mkdir()
    project_b.mkdir()
    builder = ContextBuilder(agent_home)

    prompt_a = builder.build_system_prompt(workspace=project_a)
    prompt_b = builder.build_system_prompt(workspace=project_b)
    marker = "# Current Project"
    prefix_a = prompt_a[: prompt_a.index(marker)]
    prefix_b = prompt_b[: prompt_b.index(marker)]

    assert prefix_a == prefix_b
    assert "# Tool contracts" in prefix_a
    assert str(project_a.resolve()) not in prefix_a
    assert str(project_b.resolve()) not in prefix_b
    assert prompt_a == builder.build_system_prompt(workspace=project_a)


@pytest.mark.parametrize("selected_project", [False, True])
def test_system_prompt_reflects_current_dream_memory_contract(tmp_path, selected_project) -> None:
    workspace = _make_workspace(tmp_path)
    builder = ContextBuilder(workspace)
    project = tmp_path / "project" if selected_project else workspace
    project.mkdir(exist_ok=True)

    prompt = builder.build_system_prompt(workspace=project)

    assert "memory/history.jsonl" in prompt
    assert (
        "Only Dream memory-consolidation tasks may edit the profile and long-term memory files "
        "listed above."
    ) in prompt


def test_provider_context_appended_after_user_content(tmp_path) -> None:
    workspace = _make_workspace(tmp_path)
    builder = ContextBuilder(workspace)

    messages = builder.build_messages(
        history=[],
        current_message="hello world",
        channel="cli",
        runtime_context_blocks=[
            RuntimeContextBlock(source="test", content="provider context"),
        ],
    )

    content = messages[-1]["content"]
    user_pos = content.find("hello world")
    context_pos = content.find("provider context")
    assert user_pos < context_pos, "user content must precede provider context"


def test_execution_rules_in_system_prompt(tmp_path) -> None:
    """Execution rules should appear in the system prompt via the default templates."""
    from mokli.utils.helpers import sync_workspace_templates

    workspace = _make_workspace(tmp_path)
    sync_workspace_templates(workspace, silent=True)
    builder = ContextBuilder(workspace)

    prompt = builder.build_system_prompt()
    assert "clear operator request as authorization" in prompt
    assert "Prefer read-only tools before" in prompt
    assert "Ask before destructive or irreversible actions" in prompt


def test_execution_rules_reach_existing_workspace_soul(tmp_path) -> None:
    """An untouched legacy SOUL is upgraded in memory without overwriting the file."""
    workspace = _make_workspace(tmp_path)
    legacy_soul = (
        pkg_files("mokli") / "templates" / "legacy" / "SOUL.md"
    ).read_text(encoding="utf-8")
    legacy_rule = "For multi-step tasks, outline the plan first and wait for user confirmation."
    soul_path = workspace / "SOUL.md"
    soul_path.write_text(legacy_soul, encoding="utf-8")
    builder = ContextBuilder(workspace)

    prompt = builder.build_system_prompt()
    current_rule = "Treat a clear operator request as authorization"

    assert legacy_rule not in prompt
    assert "I am mokli" not in prompt
    assert current_rule in prompt
    assert soul_path.read_text(encoding="utf-8") == legacy_soul


def test_pre_single_persona_soul_is_upgraded_in_memory(tmp_path) -> None:
    """The former default SOUL (second persona section) is replaced by the bundled one."""
    workspace = _make_workspace(tmp_path)
    old_soul = (
        "# Soul\n\nI am mokli 🐈, a personal AI assistant.\n\n"
        "## Core Principles\n\n- Solve by doing.\n\n"
        "## Gold agent (when gold is the job)\n\n- Tone tracks the tape.\n"
    )
    soul_path = workspace / "SOUL.md"
    soul_path.write_text(old_soul, encoding="utf-8")

    prompt = ContextBuilder(workspace).build_system_prompt()

    assert "I am mokli" not in prompt
    assert "🐈" not in prompt
    assert "I am Mokli." in prompt
    assert soul_path.read_text(encoding="utf-8") == old_soul


def test_customized_soul_is_kept_and_product_name_rendered(tmp_path) -> None:
    workspace = _make_workspace(tmp_path)
    (workspace / "SOUL.md").write_text(
        "# Soul\n\nI am {product_name}, and I keep {custom} braces.\n", encoding="utf-8"
    )
    from mokli.agent.prompt.composer import PromptSettings

    builder = ContextBuilder(workspace, prompt_settings=PromptSettings(product_name="GoldDesk"))
    prompt = builder.build_system_prompt()

    assert "I am GoldDesk, and I keep {custom} braces." in prompt


def test_default_soul_template_keeps_execution_policy_in_tool_contract() -> None:
    """SOUL owns voice while the always-injected layers own execution policy."""
    from mokli.agent.prompt.composer import load_layer

    soul = (pkg_files("mokli") / "templates" / "SOUL.md").read_text(encoding="utf-8")
    contract = load_layer("40_tool_contracts.md")
    behaviour = load_layer("60_behaviour.md")

    assert "## Execution Rules" not in soul
    assert "clear operator request" not in soul
    assert "clear operator request as authorization" in contract
    assert "destructive or irreversible actions" in behaviour


def test_channel_format_hint_telegram(tmp_path) -> None:
    """Telegram channel should get messaging-app format hint."""
    workspace = _make_workspace(tmp_path)
    builder = ContextBuilder(workspace)

    prompt = builder.build_system_prompt(channel="telegram")
    assert "Format Hint" in prompt
    assert "messaging app" in prompt


def test_channel_format_hint_whatsapp(tmp_path) -> None:
    """WhatsApp should get plain-text format hint."""
    workspace = _make_workspace(tmp_path)
    builder = ContextBuilder(workspace)

    prompt = builder.build_system_prompt(channel="whatsapp")
    assert "Format Hint" in prompt
    assert "plain text only" in prompt


def test_channel_format_hint_absent_for_unknown(tmp_path) -> None:
    """Unknown or None channel should not inject a format hint."""
    workspace = _make_workspace(tmp_path)
    builder = ContextBuilder(workspace)

    prompt = builder.build_system_prompt(channel=None)
    assert "Format Hint" not in prompt

    prompt2 = builder.build_system_prompt(channel="feishu")
    assert "Format Hint" not in prompt2


def test_build_messages_passes_channel_to_system_prompt(tmp_path) -> None:
    """build_messages should pass channel through to build_system_prompt."""
    workspace = _make_workspace(tmp_path)
    builder = ContextBuilder(workspace)

    messages = builder.build_messages(
        history=[], current_message="hi",
        channel="telegram",
    )
    system = messages[0]["content"]
    assert "Format Hint" in system
    assert "messaging app" in system


def test_system_prompt_keeps_message_tool_out_of_current_chat_replies(tmp_path) -> None:
    workspace = _make_workspace(tmp_path)
    builder = ContextBuilder(workspace)

    prompt = builder.build_system_prompt(channel="slack")

    assert "never for normal replies here" in prompt
    assert "| use it for normal replies in the current conversation |" in prompt
    assert "sending files and images" in prompt
    assert "call them first and answer once with their results" in prompt


def test_memory_skill_is_lazy_loaded_from_skills_index(tmp_path) -> None:
    """Memory search guidance should be discoverable without loading its full body."""
    workspace = _make_workspace(tmp_path)
    builder = ContextBuilder(workspace)

    prompt = builder.build_system_prompt()

    assert "### Skill: memory" not in prompt
    assert "**memory**" in prompt
    assert "Search Past Events" not in prompt
    assert "Examples (replace `keyword`)" not in prompt


def test_fresh_workspace_omits_default_prompt_scaffolding(tmp_path) -> None:
    from mokli.utils.helpers import sync_workspace_templates

    workspace = _make_workspace(tmp_path)
    sync_workspace_templates(workspace, silent=True)

    prompt = ContextBuilder(workspace).build_system_prompt()

    assert "## AGENTS.md" not in prompt
    assert "## USER.md" not in prompt
    assert "8281248569" not in prompt
    assert "(your name)" not in prompt
    assert prompt.count("never for normal replies here") == 1
    assert prompt.count("# Tool contracts") == 1


def test_template_memory_md_is_skipped(tmp_path) -> None:
    """MEMORY.md matching the bundled template should not inject the Memory section."""
    workspace = _make_workspace(tmp_path)
    from mokli.utils.helpers import sync_workspace_templates
    sync_workspace_templates(workspace, silent=True)

    builder = ContextBuilder(workspace)
    prompt = builder.build_system_prompt()

    # This block is produced only when populated long-term memory is injected.
    assert "# Memory\n\n## Long-term Memory" not in prompt
    assert "This file is automatically updated by mokli" not in prompt


def test_customized_memory_md_is_injected(tmp_path, monkeypatch) -> None:
    """A Dream-populated MEMORY.md should be injected normally."""
    workspace = _make_workspace(tmp_path)
    from mokli.utils.helpers import sync_workspace_templates
    sync_workspace_templates(workspace, silent=True)

    (workspace / "memory" / "MEMORY.md").write_text(
        "# Long-term Memory\n\nUser prefers dark mode.\n", encoding="utf-8"
    )

    builder = ContextBuilder(workspace)
    read_memory = builder.memory.read_memory
    calls = 0

    def tracked_read_memory() -> str:
        nonlocal calls
        calls += 1
        return read_memory()

    monkeypatch.setattr(builder.memory, "read_memory", tracked_read_memory)
    prompt = builder.build_system_prompt()

    assert "# Memory\n\n## Long-term Memory" in prompt
    assert "User prefers dark mode" in prompt
    assert calls == 1
