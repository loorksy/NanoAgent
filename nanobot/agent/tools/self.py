"""Self tool config stub — removed from gold agent."""

from __future__ import annotations

from nanobot.config_base import Base


class MyToolConfig(Base):
    """Self-inspection tool configuration (legacy config surface)."""

    enable: bool = False
    allow_set: bool = False
