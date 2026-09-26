"""Selected provider models shown in the chat picker."""

from __future__ import annotations

from typing import Any

from loguru import logger

from nanobot.config.schema import Config


def _preset_names(config: Config) -> list[str]:
    """Preset names in call order, or nothing when the user has not chosen models."""
    defaults = config.agents.defaults
    primary = defaults.model_preset
    if not primary or primary == "default" or primary not in config.model_presets:
        return []
    names = [primary]
    for fallback in defaults.fallback_models:
        if not isinstance(fallback, str):
            return []
        names.append(fallback)
    return names


def chat_model_rows(config: Config) -> list[dict[str, str]]:
    """Models the user chose, in call order. The primary model is first."""
    order = _preset_names(config)
    if not order:
        return []
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for name in order:
        preset = config.model_presets.get(name)
        if preset is None:
            continue
        model_id = preset.model.strip()
        if not model_id or model_id in seen:
            continue
        seen.add(model_id)
        rows.append({"id": model_id, "name": model_id, "preset": name})
    return rows


def public_chat_models(config: Config) -> list[dict[str, str]]:
    """Chat-picker rows without the internal preset name."""
    return [{"id": row["id"], "name": row["name"]} for row in chat_model_rows(config)]


def preset_for_chat_model(config: Config, model_id: str) -> str | None:
    """Map a chat model id back to the preset that should run."""
    for row in chat_model_rows(config):
        if model_id == row["id"] or model_id == row["preset"]:
            return row["preset"]
    return None


def apply_session_model(agent: Any, session_key: str, model_id: str) -> None:
    """Point one chat session at the preset for ``model_id`` when it is known."""
    from nanobot.config.loader import load_config

    preset = preset_for_chat_model(load_config(), model_id)
    if preset is None:
        return
    refresh = getattr(agent, "refresh_runtime_config", None)
    if callable(refresh):
        try:
            refresh()
        except Exception:
            logger.warning("chat model refresh failed")
    setter = getattr(agent, "set_session_model_preset", None)
    if not callable(setter):
        return
    try:
        setter(session_key, preset)
    except Exception:
        logger.warning("chat model selection failed")
