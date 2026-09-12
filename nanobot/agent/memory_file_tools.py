"""Restricted file tools for Dream memory consolidation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nanobot.agent.tools.base import Tool, ToolResult, tool_parameters
from nanobot.agent.tools.schema import IntegerSchema, StringSchema, tool_parameters_schema


def _allowed(path: Path, allowed_files: tuple[Path, ...]) -> bool:
    try:
        resolved = path.resolve()
    except OSError:
        return False
    return any(resolved == candidate.resolve() for candidate in allowed_files)


@tool_parameters(
    tool_parameters_schema(
        path=StringSchema("Path to a memory file"),
        offset=IntegerSchema("Line offset (0-based)"),
        limit=IntegerSchema("Maximum lines to read"),
        required=["path"],
    )
)
class DreamReadFileTool(Tool):
    _plugin_discoverable = False

    def __init__(self, *, allowed_files: tuple[Path, ...]) -> None:
        self._allowed_files = allowed_files

    @classmethod
    def create(cls, ctx: Any) -> Tool:
        raise NotImplementedError

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read one of the agent memory files (SOUL.md, USER.md, memory/MEMORY.md)."

    @property
    def read_only(self) -> bool:
        return True

    async def execute(
        self,
        path: str,
        offset: int = 0,
        limit: int = 500,
        **kwargs: Any,
    ) -> str:
        target = Path(path)
        if not _allowed(target, self._allowed_files):
            return ToolResult.error("Path not allowed for Dream memory edits.")
        if not target.exists():
            return ""
        lines = target.read_text(encoding="utf-8").splitlines()
        chunk = lines[offset : offset + max(1, limit)]
        return "\n".join(chunk)


@tool_parameters(
    tool_parameters_schema(
        path=StringSchema("Path to a memory file"),
        old_string=StringSchema("Text to replace"),
        new_string=StringSchema("Replacement text"),
        required=["path", "old_string", "new_string"],
    )
)
class DreamEditFileTool(Tool):
    _plugin_discoverable = False

    def __init__(self, *, allowed_files: tuple[Path, ...]) -> None:
        self._allowed_files = allowed_files

    @classmethod
    def create(cls, ctx: Any) -> Tool:
        raise NotImplementedError

    @property
    def name(self) -> str:
        return "edit_file"

    @property
    def description(self) -> str:
        return "Edit one of the agent memory files."

    async def execute(
        self,
        path: str,
        old_string: str,
        new_string: str,
        **kwargs: Any,
    ) -> str:
        target = Path(path)
        if not _allowed(target, self._allowed_files):
            return ToolResult.error("Path not allowed for Dream memory edits.")
        text = target.read_text(encoding="utf-8") if target.exists() else ""
        if old_string not in text:
            return ToolResult.error("old_string not found in file.")
        target.write_text(text.replace(old_string, new_string, 1), encoding="utf-8")
        return "OK"


@tool_parameters(
    tool_parameters_schema(
        path=StringSchema("Path to a memory file"),
        content=StringSchema("Full file content"),
        required=["path", "content"],
    )
)
class DreamWriteFileTool(Tool):
    _plugin_discoverable = False

    def __init__(self, *, allowed_files: tuple[Path, ...]) -> None:
        self._allowed_files = allowed_files

    @classmethod
    def create(cls, ctx: Any) -> Tool:
        raise NotImplementedError

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Overwrite one of the agent memory files."

    async def execute(self, path: str, content: str, **kwargs: Any) -> str:
        target = Path(path)
        if not _allowed(target, self._allowed_files):
            return ToolResult.error("Path not allowed for Dream memory edits.")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return "OK"
