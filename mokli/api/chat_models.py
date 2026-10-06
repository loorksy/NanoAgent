"""Selected provider models shown in the chat picker."""

from __future__ import annotations

from typing import Any

from loguru import logger

from mokli.config.schema import Config


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


def canonical_chat_model_id(
    config: Config,
    requested: object,
    *,
    alias: str = "mokli",
) -> str | None:
    """Map a selector value to the provider model id that should run.

    ``None`` means the settings primary (no per-chat override). A returned id
    is one the user selected in settings. Any other non-empty value is rejected
    so the call cannot silently keep a different model.
    """
    if requested is None:
        return None
    if not isinstance(requested, str):
        raise ValueError("model")
    chosen = requested.strip()
    if not chosen or chosen == alias or chosen == "mokli":
        return None
    if chosen.startswith("mokli."):
        chosen = chosen[len("mokli.") :].strip()
        if not chosen or chosen == "mokli":
            return None
    elif "." in chosen:
        head, tail = chosen.split(".", 1)
        tail = tail.strip()
        if head and "/" not in head and "/" in tail:
            chosen = tail
            if not chosen or chosen == "mokli":
                return None
    if preset_for_chat_model(config, chosen) is None:
        raise ValueError(chosen)
    return chosen


def apply_session_model(agent: Any, session_key: str, model_id: str) -> bool:
    """Point one chat session at the preset for ``model_id``.

    Returns false when ``model_id`` is not one of the models the user selected,
    so callers can refuse the turn instead of running a different model.
    """
    from mokli.config.loader import load_config

    preset = preset_for_chat_model(load_config(), model_id)
    if preset is None:
        return False
    refresh = getattr(agent, "refresh_runtime_config", None)
    if callable(refresh):
        try:
            refresh()
        except Exception:
            logger.warning("chat model refresh failed")
    setter = getattr(agent, "set_session_model_preset", None)
    if not callable(setter):
        return False
    try:
        setter(session_key, preset)
    except Exception:
        logger.warning("chat model selection failed")
        return False
    return True


def clear_session_model(agent: Any, session_key: str) -> bool:
    """Drop a per-chat override so the next turn uses the settings primary.

    Returns false when the override could not be cleared. Callers must not
    run the turn on the previous preset after a failed clear.
    """
    clearer = getattr(agent, "clear_session_model_preset", None)
    if not callable(clearer):
        logger.warning("chat model clear unavailable")
        return False
    try:
        clearer(session_key)
    except Exception:
        logger.warning("chat model clear failed", exc_info=True)
        return False
    return True


def listed_model_ids(config: Config, alias: str) -> list[str]:
    """Selector ids: the connection alias, then each model the user chose."""
    ids = [alias]
    seen = {alias}
    for row in public_chat_models(config):
        model_id = row["id"]
        if model_id in seen:
            continue
        seen.add(model_id)
        ids.append(model_id)
    return ids
