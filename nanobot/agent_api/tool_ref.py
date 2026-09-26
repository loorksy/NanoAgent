"""Process-wide handle to the live gold-agent tool registry."""

from __future__ import annotations

from typing import Any

_registry: Any = None


def bind_tool_registry(registry: Any) -> None:
    """Remember the registry the running agent actually executes."""
    global _registry
    _registry = registry


def tool_registry() -> Any:
    return _registry
