"""Provider linking for the Open WebUI fork.

Writes go through the same settings functions as the legacy Models page.
Responses keep API keys and ``CLAUDE_CODE_OAUTH_TOKEN`` off the wire: the
browser only sees a masked hint.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from nanobot.agent_api.errors import ApiError
from nanobot.agent_api.events import JsonObject
from nanobot.agent_api.tool_ref import refresh_bound_runtime
from nanobot.config.loader import load_config
from nanobot.webui.claude_code_oauth import apply_claude_code_oauth_token, public_status
from nanobot.webui.claude_code_oauth_flow import complete_connect, start_connect_payload
from nanobot.webui.settings_api import (
    complete_oauth_provider as finish_oauth_provider,
)
from nanobot.webui.settings_api import (
    create_provider_settings,
    login_oauth_provider,
    logout_oauth_provider,
    update_provider_settings,
)
from nanobot.webui.settings_contracts import WebUISettingsError
from nanobot.webui.settings_models import model_settings_payload, oauth_provider_status
from nanobot.webui.settings_services import WebUIOAuthFlowRegistry, WebUISettingsConfig

_NAME = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
_MAX_SECRET = 16384
_ROW_FIELDS = (
    "name",
    "label",
    "is_custom",
    "configured",
    "auth_type",
    "api_key_required",
    "api_key_hint",
    "api_base",
    "default_api_base",
    "cli_oauth_hint",
    "oauth_account",
    "oauth_login_supported",
)
_FLOW_FIELDS = (
    "status",
    "provider",
    "flow_id",
    "authorization_url",
    "expires_in",
    "completion_input",
)


def _settings_error(exc: WebUISettingsError, secret: str | None = None) -> ApiError:
    message = exc.message
    if secret and secret in message:
        message = "provider_error"
    status = exc.status if isinstance(exc.status, int) else 400
    return ApiError(status, "provider_error", details={"message": message})


def _config_path(config_path: Path | None) -> Path | None:
    return config_path


def _locked(config_path: Path | None, operation: Any) -> Any:
    path = _config_path(config_path)
    if path is None:
        return operation(None)
    return WebUISettingsConfig(path).run_serialized(operation)


def _public_row(row: dict[str, Any]) -> dict[str, Any]:
    public: dict[str, Any] = {}
    for key in _ROW_FIELDS:
        if key not in row:
            continue
        value = row[key]
        if value is None or isinstance(value, (str, bool, int)):
            public[key] = value
    return public


def _guard(document: dict[str, Any], secrets: list[str]) -> dict[str, Any]:
    encoded = str(document)
    for secret in secrets:
        if secret and len(secret) >= 8 and secret in encoded:
            raise ApiError(500, "provider_error", details={"message": "provider_error"})
    return document


def provider_document(config_path: Path | None = None) -> dict[str, Any]:
    """Configured and available providers. No API keys and no OAuth token."""
    config = load_config(config_path) if config_path is not None else load_config()
    payload = model_settings_payload(config, oauth_status=oauth_provider_status)
    rows = payload.get("providers")
    providers = [
        _public_row(row)
        for row in rows
        if isinstance(row, dict)
    ] if isinstance(rows, list) else []
    return {"providers": providers, "claude_code": public_status()}


def _string(body: JsonObject, field: str, *, required: bool = False) -> str | None:
    if field not in body:
        if required:
            raise ApiError(400, "invalid_field", details={"field": field})
        return None
    value = body.get(field)
    if not isinstance(value, str):
        raise ApiError(400, "invalid_field", details={"field": field})
    cleaned = value.strip()
    if len(cleaned) > _MAX_SECRET:
        raise ApiError(400, "invalid_field", details={"field": field})
    if required and not cleaned:
        raise ApiError(400, "invalid_field", details={"field": field})
    return cleaned


def _query_from(body: JsonObject, fields: dict[str, str]) -> dict[str, list[str]]:
    query: dict[str, list[str]] = {}
    for source, dest in fields.items():
        if source not in body:
            continue
        value = _string(body, source)
        if value is None:
            continue
        if source == "api_key" and not value:
            continue
        query[dest] = [value]
    return query


def _checked_name(name: str) -> str:
    if not _NAME.fullmatch(name):
        raise ApiError(400, "invalid_field", details={"field": "provider"})
    return name


def save_api_provider(
    name: str,
    body: JsonObject,
    *,
    config_path: Path | None,
) -> dict[str, Any]:
    provider = _checked_name(name)
    secret = _string(body, "api_key") or ""
    query = {"provider": [provider], **_query_from(body, {
        "api_key": "apiKey",
        "api_base": "apiBase",
        "display_name": "displayName",
    })}

    def _save(path: Path | None) -> None:
        try:
            update_provider_settings(query, config_path=path)
        except WebUISettingsError as exc:
            raise _settings_error(exc, secret or None) from exc

    _locked(config_path, _save)
    refresh_bound_runtime()
    return _guard(provider_document(config_path), [secret])


def create_custom_provider(body: JsonObject, *, config_path: Path | None) -> dict[str, Any]:
    secret = _string(body, "api_key") or ""
    query = _query_from(body, {
        "name": "name",
        "api_key": "apiKey",
        "api_base": "apiBase",
    })
    if "name" not in query:
        raise ApiError(400, "invalid_field", details={"field": "name"})

    created: dict[str, str] = {}

    def _save(path: Path | None) -> None:
        try:
            payload = create_provider_settings(query, config_path=path)
        except WebUISettingsError as exc:
            raise _settings_error(exc, secret or None) from exc
        key = payload.get("created_provider")
        if isinstance(key, str):
            created["name"] = key

    _locked(config_path, _save)
    refresh_bound_runtime()
    document = provider_document(config_path)
    if "name" in created:
        document["created_provider"] = created["name"]
    return _guard(document, [secret])


def save_claude_token(body: JsonObject, *, config_path: Path | None) -> dict[str, Any]:
    clear = body.get("clear") is True
    token = "" if clear else (_string(body, "token") or "")
    if not clear and not token:
        raise ApiError(400, "invalid_field", details={"field": "token"})
    try:
        apply_claude_code_oauth_token(None if clear else token)
    except WebUISettingsError as exc:
        raise _settings_error(exc, token or None) from exc
    refresh_bound_runtime()
    return _guard(provider_document(config_path), [] if clear else [token])


def claude_connect(flows: WebUIOAuthFlowRegistry) -> dict[str, Any]:
    started = start_connect_payload(flows)
    return {key: started[key] for key in _FLOW_FIELDS if key in started}


def claude_callback(
    body: JsonObject,
    flows: WebUIOAuthFlowRegistry,
    *,
    config_path: Path | None,
) -> dict[str, Any]:
    flow_id = _string(body, "flow_id")
    code = _string(body, "code")
    state = _string(body, "state")
    pasted = _string(body, "authorization_response")
    try:
        complete_connect(
            oauth_flows=flows,
            flow_id=flow_id,
            authorization_response=pasted,
            code=code,
            state=state,
        )
    except WebUISettingsError as exc:
        secret = pasted or code or ""
        raise _settings_error(exc, secret or None) from exc
    refresh_bound_runtime()
    return _guard(provider_document(config_path), [pasted or "", code or ""])


def _public_flow(payload: dict[str, Any]) -> dict[str, Any]:
    public: dict[str, Any] = {}
    for key in _FLOW_FIELDS:
        if key not in payload:
            continue
        value = payload[key]
        if value is None or isinstance(value, (str, bool, int)):
            public[key] = value
    return public


def provider_oauth(
    name: str,
    body: JsonObject,
    flows: WebUIOAuthFlowRegistry,
    *,
    config_path: Path | None,
) -> dict[str, Any]:
    provider = _checked_name(name)
    action = _string(body, "action", required=True)
    query: dict[str, list[str]] = {"provider": [provider], "remote_browser": ["true"]}
    flow_id = _string(body, "flow_id")
    if flow_id:
        query["flow_id"] = [flow_id]
    pasted = _string(body, "authorization_response") or ""

    def _run() -> dict[str, Any]:
        try:
            if action == "login":
                return login_oauth_provider(
                    query,
                    oauth_flows=flows,
                    config_path=config_path,
                )
            if action == "logout":
                return logout_oauth_provider(
                    query,
                    oauth_flows=flows,
                    config_path=config_path,
                )
            if action == "complete":
                return finish_oauth_provider(
                    query,
                    pasted or None,
                    oauth_flows=flows,
                    config_path=config_path,
                )
        except WebUISettingsError as exc:
            raise _settings_error(exc, pasted or None) from exc
        raise ApiError(400, "invalid_field", details={"field": "action"})

    # login_oauth_provider also calls settings_payload on some success paths.
    # Those paths are replaced below when the result is not an in-progress flow.
    result = _run()
    status = result.get("status") if isinstance(result, dict) else None
    if status in {"authorization_required", "pending"}:
        return _public_flow(result)
    refresh_bound_runtime()
    return _guard(provider_document(config_path), [pasted])
