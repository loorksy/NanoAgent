"""Agent API configuration DTO and defensive loader.

``AgentApiConfig`` is defined here (not in ``mokli/config/schema.py``) so the
package can be developed independently; the loader accepts the value from the
root ``Config`` once the coordinator adds an ``agent_api`` field there, and
falls back to the raw ``agentApi`` / ``agent_api`` key of the config file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from pydantic import BaseModel, Field, ValidationError

from mokli.config_base import Base

CONFIG_KEYS: tuple[str, ...] = ("agentApi", "agent_api")


class AgentApiConfig(Base):
    """Settings for the aiohttp Agent API listener."""

    enabled: bool = True
    host: str = "127.0.0.1"
    port: int = 8766
    token_ttl_seconds: int = 900
    event_retention_days: int = 7
    cors_origins: list[str] = Field(default_factory=list)
    # Optional static admin credential (kind ``service``, all scopes). When empty a
    # random one is generated at startup and written to ``<workspace>/agent_api/admin_token``.
    bootstrap_token: str = ""
    max_events_per_session: int = 5000
    request_timeout_seconds: float = 900.0
    # Also serve the OpenAI-compatible ``/v1/chat/completions`` + ``/v1/models`` on this
    # listener (Mokli's model connection); authenticated by the same bearer tokens.
    openai_compat: bool = True
    openai_model_name: str = "mokli"


def _from_mapping(blob: object) -> AgentApiConfig | None:
    if not isinstance(blob, dict):
        return None
    try:
        return AgentApiConfig.model_validate(cast(dict[str, object], blob))
    except ValidationError:
        return None


def _from_file(path: Path | None) -> AgentApiConfig | None:
    if path is None or not path.exists():
        return None
    try:
        raw: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    data = cast(dict[str, object], raw)
    for key in CONFIG_KEYS:
        found = _from_mapping(data.get(key))
        if found is not None:
            return found
    return None


def load_agent_api_config(
    config: object,
    *,
    config_path: Path | None = None,
) -> AgentApiConfig:
    """Resolve the Agent API settings from a root config object or its source file."""
    direct = getattr(config, "agent_api", None)
    if isinstance(direct, AgentApiConfig):
        return direct
    if isinstance(direct, BaseModel):
        found = _from_mapping(direct.model_dump(by_alias=False))
        if found is not None:
            return found
    extra = getattr(config, "model_extra", None)
    if isinstance(extra, dict):
        extra_map = cast(dict[str, object], extra)
        for key in CONFIG_KEYS:
            found = _from_mapping(extra_map.get(key))
            if found is not None:
                return found
    from_file = _from_file(config_path)
    if from_file is not None:
        return from_file
    return AgentApiConfig()
