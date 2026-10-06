"""Tests for tool plugin architecture: ToolLoader, ToolContext, metadata."""
from __future__ import annotations

from dataclasses import fields
from typing import Any
from unittest.mock import MagicMock

from mokli.agent.tools.base import Tool
from mokli.agent.tools.context import ToolContext
from mokli.agent.tools.loader import _SKIP_MODULES, ToolLoader


class _MinimalTool(Tool):
    @property
    def name(self) -> str:
        return "test_minimal"

    @property
    def description(self) -> str:
        return "A test tool"

    @property
    def parameters(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def execute(self, **kwargs: Any) -> Any:
        return "ok"


def test_tool_default_config_cls_is_none():
    assert _MinimalTool.config_cls() is None


def test_tool_default_config_key_is_empty():
    assert _MinimalTool.config_key == ""


def test_tool_default_enabled_is_true():
    assert _MinimalTool.enabled(None) is True


def test_tool_default_create_returns_instance():
    tool = _MinimalTool.create(None)
    assert isinstance(tool, _MinimalTool)
    assert tool.name == "test_minimal"


def test_tool_plugin_discoverable_default_is_true():
    assert _MinimalTool._plugin_discoverable is True


# --- ToolContext tests ---


def test_tool_context_has_required_fields():
    field_names = {f.name for f in fields(ToolContext)}
    required = {
        "config", "workspace", "bus", "subagent_manager",
        "cron_service", "exec_session_manager", "file_state_store",
        "provider_snapshot_loader", "image_generation_provider_configs", "timezone",
        "runtime_control",
    }
    assert required <= field_names


def test_tool_context_defaults():
    ctx = ToolContext(config=None, workspace="/tmp")
    assert ctx.bus is None
    assert ctx.subagent_manager is None
    assert ctx.cron_service is None
    assert ctx.exec_session_manager is None
    assert ctx.provider_snapshot_loader is None
    assert ctx.image_generation_provider_configs is None
    assert ctx.runtime_control is None
    assert ctx.timezone == "UTC"


# --- ToolLoader tests ---


def test_skip_modules_excludes_infrastructure():
    infra = {"base", "schema", "registry", "context", "loader", "config",
             "file_state", "sandbox", "mcp", "__init__"}
    assert infra <= _SKIP_MODULES


def test_discover_finds_concrete_tools():
    loader = ToolLoader()
    discovered = loader.discover()
    class_names = {cls.__name__ for cls in discovered}
    assert "MessageTool" in class_names
    assert "SpawnTool" in class_names
    assert "CronTool" in class_names
    assert "WebSearchTool" in class_names
    assert "AnalyzeGoldTool" in class_names
    assert "RunTradingKernelTool" in class_names
    # Generic coding tools were removed from the gold agent.
    assert "ExecTool" not in class_names
    assert "ReadFileTool" not in class_names
    assert "ApplyPatchTool" not in class_names


def test_discover_excludes_abstract_and_mcp():
    loader = ToolLoader()
    discovered = loader.discover()
    class_names = {cls.__name__ for cls in discovered}
    assert "_FsTool" not in class_names
    assert "_SearchTool" not in class_names
    assert "MCPToolWrapper" not in class_names
    assert "MCPResourceWrapper" not in class_names
    assert "MCPPromptWrapper" not in class_names


def test_discover_skips_private_classes():
    loader = ToolLoader()
    discovered = loader.discover()
    for cls in discovered:
        assert not cls.__name__.startswith("_")


# --- Task 5: MessageTool, SpawnTool, CronTool ---


async def test_message_tool_create():
    from mokli.agent.tools.message import MessageTool
    mock_bus = MagicMock()
    mock_config = MagicMock()
    ctx = ToolContext(config=mock_config, workspace="/tmp", bus=mock_bus)
    tool = MessageTool.create(ctx)
    assert isinstance(tool, MessageTool)


def test_spawn_tool_create():
    from mokli.agent.tools.spawn import SpawnTool
    mock_mgr = MagicMock()
    mock_config = MagicMock()
    ctx = ToolContext(config=mock_config, workspace="/tmp", subagent_manager=mock_mgr)
    tool = SpawnTool.create(ctx)
    assert isinstance(tool, SpawnTool)


def test_cron_tool_enabled_without_service():
    from mokli.agent.tools.cron import CronTool
    mock_config = MagicMock()
    ctx = ToolContext(config=mock_config, workspace="/tmp", cron_service=None)
    assert CronTool.enabled(ctx) is False


def test_cron_tool_enabled_with_service():
    from mokli.agent.tools.cron import CronTool
    mock_service = MagicMock()
    mock_config = MagicMock()
    ctx = ToolContext(config=mock_config, workspace="/tmp", cron_service=mock_service)
    assert CronTool.enabled(ctx) is True


def test_cron_tool_create():
    from mokli.agent.tools.cron import CronTool
    mock_service = MagicMock()
    mock_config = MagicMock()
    ctx = ToolContext(
        config=mock_config, workspace="/tmp",
        cron_service=mock_service, timezone="Asia/Shanghai",
    )
    tool = CronTool.create(ctx)
    assert isinstance(tool, CronTool)


# --- Task 6: WebTools ---


def test_web_tools_config_cls():
    from mokli.agent.tools.web import WebFetchTool, WebSearchTool, WebToolsConfig
    assert WebSearchTool.config_key == "web"
    assert WebSearchTool.config_cls() is WebToolsConfig
    assert WebFetchTool.config_key == "web"
    assert WebFetchTool.config_cls() is WebToolsConfig


def test_web_tools_enabled():
    from mokli.agent.tools.web import WebSearchTool
    mock_config = MagicMock()
    mock_config.web.enable = True
    ctx = ToolContext(config=mock_config, workspace="/tmp")
    assert WebSearchTool.enabled(ctx) is True
    mock_config.web.enable = False
    assert WebSearchTool.enabled(ctx) is False


def test_web_search_tool_create():
    from mokli.agent.tools.web import WebSearchTool
    mock_config = MagicMock()
    mock_config.web.enable = True
    mock_config.web.search = MagicMock()
    mock_config.web.proxy = None
    mock_config.web.user_agent = None
    ctx = ToolContext(config=mock_config, workspace="/tmp")
    tool = WebSearchTool.create(ctx)
    assert isinstance(tool, WebSearchTool)


def test_web_fetch_tool_create():
    from mokli.agent.tools.web import WebFetchTool
    mock_config = MagicMock()
    mock_config.web.enable = True
    mock_config.web.fetch = MagicMock()
    mock_config.web.proxy = None
    mock_config.web.user_agent = None
    ctx = ToolContext(config=mock_config, workspace="/tmp")
    tool = WebFetchTool.create(ctx)
    assert isinstance(tool, WebFetchTool)


# --- Task 7: MCP wrappers ---


def test_mcp_wrappers_not_discoverable():
    from mokli.agent.tools.mcp import MCPPromptWrapper, MCPResourceWrapper, MCPToolWrapper
    assert MCPToolWrapper._plugin_discoverable is False
    assert MCPResourceWrapper._plugin_discoverable is False
    assert MCPPromptWrapper._plugin_discoverable is False


# --- Task 10: Integration test ---


def test_loader_registers_gold_agent_tool_set(tmp_path):
    """The loader wires the trading tool set; generic coding tools stay out."""
    from mokli.agent.tools.loader import ToolLoader
    from mokli.agent.tools.registry import ToolRegistry
    from mokli.config.schema import ToolsConfig

    ctx = ToolContext(
        config=ToolsConfig(),
        workspace=str(tmp_path),
        bus=MagicMock(),
        subagent_manager=MagicMock(),
        cron_service=MagicMock(),
        timezone="UTC",
        runtime_control=MagicMock(),
    )
    registry = ToolRegistry()
    registered = set(ToolLoader().load(ctx, registry))

    expected = {
        "analyze_gold", "get_gold_quote", "run_trading_kernel", "run_trading_team",
        "manage_trading_plan", "get_live_recommendation", "get_gate_report",
        "mt5_propose_order", "mt5_confirm_order", "mt5_cancel_order",
        "message", "spawn", "cron", "web_search", "web_fetch",
    }
    assert expected <= registered, f"Missing tools: {expected - registered}"
    removed = {"read_file", "write_file", "edit_file", "list_dir", "exec", "exec_session", "my"}
    assert not (removed & registered), f"Removed tools still registered: {removed & registered}"
