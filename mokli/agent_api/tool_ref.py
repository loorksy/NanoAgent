"""Process-wide handle to the live gold-agent tool registry."""

from __future__ import annotations

from typing import Any

from loguru import logger

_registry: Any = None
_agent: Any = None


def bind_tool_registry(registry: Any) -> None:
    """Remember the registry the running agent actually executes."""
    global _registry
    _registry = registry


def bind_agent(agent: Any) -> None:
    """Remember the loop whose skill loader must follow config changes."""
    global _agent
    _agent = agent


def tool_registry() -> Any:
    return _registry


def refresh_bound_runtime() -> None:
    """Reload the live agent's model runtime after a provider change."""
    agent = _agent
    refresh = getattr(agent, "refresh_runtime_config", None)
    if not callable(refresh):
        return
    try:
        refresh()
    except Exception:
        logger.warning("Provider save did not refresh the live runtime")


def apply_disabled_skills(names: set[str]) -> None:
    """Push a saved disabled-skill set into the running agent, when one is bound."""
    agent = _agent
    if agent is None:
        return
    context = getattr(agent, "context", None)
    skills = getattr(context, "skills", None)
    if skills is not None:
        skills.disabled_skills = set(names)
    subagents = getattr(agent, "subagents", None)
    if subagents is not None and hasattr(subagents, "disabled_skills"):
        subagents.disabled_skills = set(names)
