"""Telegram token and WhatsApp QR connect for ``/api/v2/connect/channels``.

Status and saves go through the same channel config helpers as the legacy WebUI.
The response never includes a bot token.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any, cast

from nanobot.agent_api.errors import ApiError
from nanobot.agent_api.events import JsonObject

_CHANNEL_NAMES = ("telegram", "whatsapp")
_connectors: dict[str, Any] = {}


def channel_rows(config_path: Path) -> list[JsonObject]:
    from nanobot.channels.runtime_ref import channel_manager
    from nanobot.config.loader import load_config
    from nanobot.optional_features import optional_features_payload, with_channel_runtime_status

    config = load_config(config_path) if config_path.is_file() else None
    payload = optional_features_payload(config=config)
    manager = channel_manager()
    if manager is not None:
        payload = with_channel_runtime_status(payload, manager.get_status())
    by_name = {
        str(feature.get("name")): feature
        for feature in cast(list[object], payload.get("features", []))
        if isinstance(feature, dict)
    }
    rows: list[JsonObject] = []
    for name in _CHANNEL_NAMES:
        feature = by_name.get(name, {})
        rows.append({
            "name": name,
            "installed": bool(feature.get("installed")),
            "enabled": bool(feature.get("enabled")),
            "configured": bool(feature.get("configured")),
            "running": bool(feature.get("running")),
            "status": str(feature.get("status") or "not_enabled"),
        })
    return rows


def _load_plugin(name: str) -> Any:
    from nanobot.channels.registry import discover_plugins

    plugin = discover_plugins().get(name)
    if plugin is None:
        raise ImportError(name)
    return plugin


def _allow_install(config_path: Path) -> bool:
    from nanobot.config.loader import load_config

    if not config_path.is_file():
        return False
    try:
        return bool(load_config(config_path).tools.webui_allow_remote_package_install)
    except Exception:
        return False


def save_telegram_token(config_path: Path, token: str) -> None:
    from nanobot.webui.settings_services import WebUISettingsConfig
    from nanobot.webui.settings_system import WebUISettingsError, save_channel_config_values

    store = WebUISettingsConfig(config_path)

    def mutation(config: Any) -> list[str]:
        return save_channel_config_values(
            config,
            "telegram",
            {"channels.telegram.token": token},
            "default",
            load_channel_plugin=_load_plugin,
        )

    try:
        store.update(mutation)
    except WebUISettingsError as exc:
        status = getattr(exc, "status", 400)
        raise ApiError(
            status if isinstance(status, int) else 400,
            "channel_config_error",
            details={"message": str(getattr(exc, "message", exc))},
        ) from exc


def connector(name: str) -> Any:
    existing = _connectors.get(name)
    if existing is None:
        existing = _load_plugin(name).load_connector()
        _connectors[name] = existing
    return existing


def qr_data_url(text: str) -> str:
    """Render a pairing string as a PNG data URL. Empty when segno is absent."""
    if text.startswith("data:image/"):
        return text
    try:
        import segno
    except ImportError:
        return ""
    buffer = io.BytesIO()
    segno.make(text, error="m").save(buffer, kind="png", scale=6, border=2)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def public_connect_payload(payload: dict[str, Any]) -> JsonObject:
    public: JsonObject = {
        "session_id": str(payload.get("session_id") or ""),
        "status": str(payload.get("status") or "pending"),
        "interval_ms": int(payload.get("interval_ms") or 2000),
    }
    qr_url = payload.get("qr_url")
    if isinstance(qr_url, str) and qr_url:
        image = qr_data_url(qr_url)
        if image:
            public["qr_data_url"] = image
    return public


async def enable_channel(config_path: Path, name: str) -> bool:
    """Enable a channel and hot-reload it when the gateway manager is bound."""
    from nanobot.channels.runtime_ref import channel_manager
    from nanobot.optional_features import OptionalFeatureError, enable_optional_feature

    try:
        enable_optional_feature(
            name,
            config_path=config_path,
            allow_install=_allow_install(config_path),
        )
    except OptionalFeatureError as exc:
        raise ApiError(
            exc.status,
            "channel_enable_failed",
            details={"message": exc.message},
        ) from exc
    manager = channel_manager()
    if manager is None:
        return True
    result = manager.apply_channel_feature_action("enable", name, "default")
    if hasattr(result, "__await__"):
        result = await result
    if isinstance(result, dict) and result.get("handled") and not result.get("requires_restart"):
        return False
    return True
