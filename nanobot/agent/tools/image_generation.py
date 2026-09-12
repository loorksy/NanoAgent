"""Image generation config stub — tool removed from gold agent."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from nanobot.config_base import Base


class ImageGenerationToolConfig(Base):
    """Image generation tool configuration (legacy config surface)."""

    enabled: bool = False
    provider: str = "openrouter"
    model: str = "openai/gpt-5.4-image-2"
    default_aspect_ratio: str = "1:1"
    default_image_size: str = "1K"
    max_images_per_turn: int = Field(default=4, ge=1, le=8)
    save_dir: str = "generated"


async def request_image_generation_reload(_bus: Any, *, timeout: float = 5.0) -> dict[str, Any]:
    return {"ok": True, "skipped": True}


async def handle_runtime_control(_state: Any, _msg: Any, _registry: Any) -> bool:
    return False
