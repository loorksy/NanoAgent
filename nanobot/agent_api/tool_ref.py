"""Process-wide handle to the live gold-agent tool registry."""

from __future__ import annotations

from typing import Any

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
