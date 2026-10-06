"""Swarm team models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SwarmAgent:
    id: str
    role: str
    system_prompt: str = ""


@dataclass
class SwarmTask:
    id: str
    agent_id: str
    prompt_template: str
    depends_on: list[str] = field(default_factory=list)
    input_from: dict[str, str] = field(default_factory=dict)


@dataclass
class SwarmPreset:
    name: str
    title: str
    description: str
    agents: list[SwarmAgent]
    tasks: list[SwarmTask]
    variables: list[dict[str, Any]] = field(default_factory=list)
