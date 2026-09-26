from pathlib import Path

from nanobot.agent.memory import MemoryStore
from nanobot.agent.tools.context import ToolContext
from nanobot.agent.tools.loader import ToolLoader
from nanobot.agent.tools.registry import ToolRegistry
from nanobot.config.schema import Config


def test_dream_registry_exposes_only_memory_file_tools(tmp_path: Path) -> None:
    """Dream runs get their own read/edit/write tools, scoped to the memory files."""
    registry = MemoryStore(tmp_path).build_dream_tools()

    names = set(registry.tool_names)
    assert names == {"read_file", "edit_file", "write_file"}


def test_tool_loader_memory_scope_has_no_generic_tools() -> None:
    """The generic file/shell/message tools were removed; nothing leaks into the memory scope."""
    loader = ToolLoader()
    registry = ToolRegistry()
    ctx = ToolContext(config=Config().tools, workspace="/tmp")
    loader.load(ctx, registry, scope="memory")

    names = set(registry.tool_names)
    assert "list_dir" not in names
    assert "exec" not in names
    assert "message" not in names
