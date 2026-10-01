"""Read-only access to skill markdown and the agent profile files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mokli.agent.tools.base import Tool, ToolResult
from mokli.agent.tools.context import ToolContext
from mokli.agent.tools.schema import IntegerSchema, StringSchema, tool_parameters_schema
from mokli.trading.skill_access import SkillPathError, grep_skills, read_text, resolve_readable


class ReadFileTool(Tool):
    """Read a skill or profile file. Does not write and does not follow secrets."""

    def __init__(self, workspace: Path) -> None:
        self._workspace = workspace

    @classmethod
    def create(cls, ctx: ToolContext) -> Tool:
        return cls(Path(ctx.workspace))

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return (
            "Read a skill markdown file or one profile file "
            "(SOUL.md, USER.md, AGENTS.md, HEARTBEAT.md, memory/MEMORY.md, "
            "memory/history.jsonl). Paths outside those files are refused. "
            "This tool never writes and never reads credentials."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return tool_parameters_schema(
            path=StringSchema("Skill-relative or workspace-relative path"),
            offset=IntegerSchema(description="First line to return, 1-based", minimum=1),
            limit=IntegerSchema(description="Maximum lines to return", minimum=1, maximum=400),
            required=["path"],
        )

    @property
    def read_only(self) -> bool:
        return True

    async def execute(
        self,
        path: str = "",
        offset: int = 1,
        limit: int = 400,
        **kwargs: Any,
    ) -> Any:
        del kwargs
        try:
            resolved = resolve_readable(self._workspace, path)
            return read_text(resolved, offset=offset, limit=limit)
        except SkillPathError as exc:
            return ToolResult.error(exc.reason)


class GrepTool(Tool):
    """Literal search across skill markdown."""

    def __init__(self, workspace: Path) -> None:
        self._workspace = workspace

    @classmethod
    def create(cls, ctx: ToolContext) -> Tool:
        return cls(Path(ctx.workspace))

    @property
    def name(self) -> str:
        return "grep"

    @property
    def description(self) -> str:
        return (
            "Search skill markdown for a literal string. Use this to open one "
            "playbook or news rule instead of reading a whole encyclopedia. "
            "Results are file paths and line numbers. Credentials are not searchable."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return tool_parameters_schema(
            pattern=StringSchema("Literal text to find", min_length=1, max_length=200),
            path=StringSchema("Optional skill file or directory to search"),
            glob=StringSchema("Filename glob, default *.md"),
            required=["pattern"],
        )

    @property
    def read_only(self) -> bool:
        return True

    async def execute(
        self,
        pattern: str = "",
        path: str = "",
        glob: str = "*.md",
        **kwargs: Any,
    ) -> Any:
        del kwargs
        try:
            found = grep_skills(self._workspace, pattern, path=path, glob=glob or "*.md")
        except SkillPathError as exc:
            return ToolResult.error(exc.reason)
        return found or "no matches"
