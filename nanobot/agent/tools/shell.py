"""Exec tool config stub — shell tool removed from gold agent."""

from __future__ import annotations

from pydantic import Field

from nanobot.config_base import Base


class ExecToolConfig(Base):
    """Shell exec tool configuration (legacy config surface)."""

    enable: bool = False
    timeout: int = Field(default=60, ge=0)
    path_prepend: str = ""
    path_append: str = ""
    sandbox: str = ""
    sandbox_ro_binds: list[str] = Field(default_factory=list)
    sandbox_rw_binds: list[str] = Field(default_factory=list)
    allowed_env_keys: list[str] = Field(default_factory=list)
    allow_patterns: list[str] = Field(default_factory=list)
    deny_patterns: list[str] = Field(default_factory=list)
