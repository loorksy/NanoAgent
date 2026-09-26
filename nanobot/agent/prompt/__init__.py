"""Layered system-prompt package (identity → mission → hard law → tools → output → behaviour)."""

from nanobot.agent.prompt.composer import (
    DEFAULT_PRODUCT_NAME,
    STATIC_LAYERS,
    PromptContext,
    PromptRenderError,
    PromptSettings,
    ToolContract,
    compose_decision_prompt,
    compose_system_prompt,
    compose_team_role_prompt,
    render_tool_contracts,
)

__all__ = [
    "DEFAULT_PRODUCT_NAME",
    "STATIC_LAYERS",
    "PromptContext",
    "PromptRenderError",
    "PromptSettings",
    "ToolContract",
    "compose_decision_prompt",
    "compose_system_prompt",
    "compose_team_role_prompt",
    "render_tool_contracts",
]
