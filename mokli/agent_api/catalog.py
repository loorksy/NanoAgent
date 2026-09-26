"""Operator catalog of the skills and tools the running agent loads."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from mokli.agent.tools.context import ToolContext
from mokli.agent.tools.loader import ToolLoader
from mokli.agent.tools.registry import ToolRegistry
from mokli.agent_api.tool_ref import apply_disabled_skills, tool_registry
from mokli.config.loader import load_config
from mokli.mokli.skills_api import set_mokli_skill_enabled, mokli_skills_payload


def workspace_path(config_path: Path | None = None) -> Path:
    config = load_config(config_path)
    return Path(config.agents.defaults.workspace).expanduser()


def skill_rows(config_path: Path | None = None) -> dict[str, object]:
    """Skills the agent prompt loader sees, including disabled ones."""
    config = load_config(config_path)
    disabled = set(config.agents.defaults.disabled_skills)
    return cast(
        dict[str, object],
        mokli_skills_payload(workspace_path(config_path), disabled_skills=disabled),
    )


def set_skill_enabled(
    name: str,
    *,
    enabled: bool,
    config_path: Path | None = None,
) -> dict[str, object]:
    config = load_config(config_path)
    disabled = set(config.agents.defaults.disabled_skills)
    saved = set_mokli_skill_enabled(
        workspace_path(config_path),
        name,
        enabled=enabled,
        disabled_skills=disabled,
        config_path=config_path,
    )
    apply_disabled_skills(disabled)
    return cast(dict[str, object], saved)


def _schema_function(schema: dict[str, Any]) -> dict[str, Any]:
    function = schema.get("function")
    if isinstance(function, dict):
        return cast(dict[str, Any], function)
    return schema


def tool_rows() -> dict[str, object]:
    """Names and descriptions from the live registry, else a fresh gold load."""
    registry = tool_registry()
    if registry is None or not hasattr(registry, "get_definitions"):
        config = load_config()
        ctx = ToolContext(
            config=config.tools,
            workspace=str(workspace_path()),
            timezone=getattr(config.agents.defaults, "timezone", None) or "UTC",
        )
        registry = ToolRegistry()
        ToolLoader().load(ctx, registry)
    rows: list[dict[str, object]] = []
    for schema in registry.get_definitions():
        if not isinstance(schema, dict):
            continue
        function = _schema_function(cast(dict[str, Any], schema))
        name = function.get("name")
        if not isinstance(name, str) or not name:
            continue
        description = function.get("description")
        rows.append({
            "name": name,
            "description": description if isinstance(description, str) else "",
        })
    rows.sort(key=lambda row: str(row["name"]))
    return {"tools": rows}
