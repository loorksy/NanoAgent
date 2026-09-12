"""CLI apps tool config stub — removed from gold agent."""

from __future__ import annotations

from pydantic import Field

from nanobot.config_base import Base


class CliAppsToolConfig(Base):
    """CLI Apps tool configuration (legacy config surface)."""

    enable: bool = False
    install_timeout: int = Field(default=300, ge=1, le=3600)
    run_timeout: int = Field(default=60, ge=1, le=600)
    catalog_ttl_seconds: int = Field(default=3600, ge=60, le=86_400)
