"""Filesystem tool config stub — file tools removed from gold agent."""

from __future__ import annotations

from nanobot.config_base import Base


class FileToolsConfig(Base):
    """Filesystem tools configuration (legacy config surface)."""

    enable: bool = False
