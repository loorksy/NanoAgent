"""Provider linking for the Mokli fork.

Writes go through the same settings functions as the legacy Models page.
Responses keep API keys and ``CLAUDE_CODE_OAUTH_TOKEN`` off the wire: the
browser only sees a masked hint.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, cast

from mokli.agent_api.errors import ApiError
from mokli.agent_api.events import JsonObject
from mokli.agent_api.tool_ref import refresh_bound_runtime
from mokli.config.loader import load_config, save_config
from mokli.config.schema import Config
from mokli.mokli.claude_code_oauth import apply_claude_code_oauth_token, public_status
from mokli.mokli.claude_code_oauth_flow import complete_connect, start_connect_payload
from mokli.mokli.settings_api import (
    complete_oauth_provider as finish_oauth_provider,
)
from mokli.mokli.settings_api import (
    create_provider_settings,
    login_oauth_provider,
    logout_oauth_provider,
    provider_models_payload,
    update_provider_settings,
)
from mokli.mokli.settings_contracts import MokliSettingsError
from mokli.mokli.settings_models import (
    assign_provider_models,
    model_settings_payload,
    oauth_provider_status,
    provider_model_selection,
    resolve_settings_provider,
)
from mokli.mokli.settings_services import MokliOAuthFlowRegistry, MokliSettingsConfig

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
    "user_code",
    "expires_in",
    "completion_input",
)


def _settings_error(exc: MokliSettingsError, secret: str | None = None) -> ApiError:
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
    return MokliSettingsConfig(path).run_serialized(operation)


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


_MODALITIES = {"text", "image", "video", "audio", "file"}


def _modalities(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    found: list[str] = []
    for item in value:
        if isinstance(item, str) and item in _MODALITIES and item not in found:
            found.append(item)
    return found


def _price(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if number < 0 or number > 100_000:
        return None
    return number


def _public_model(row: dict[str, Any]) -> dict[str, Any] | None:
    model_id = row.get("id")
    if not isinstance(model_id, str) or not model_id.strip():
        return None
    public: dict[str, Any] = {"id": model_id.strip()}
    label = row.get("label")
    if isinstance(label, str) and label.strip():
        public["label"] = label.strip()[:120]
    description = row.get("description")
    if isinstance(description, str) and description.strip():
        public["description"] = description.strip()[:180]
    context_window = row.get("context_window")
    if isinstance(context_window, int) and not isinstance(context_window, bool) and context_window > 0:
        public["context_window"] = context_window
    inputs = _modalities(row.get("input_modalities"))
    outputs = _modalities(row.get("output_modalities"))
    if inputs:
        public["input_modalities"] = inputs
    if outputs:
        public["output_modalities"] = outputs
    price_in = _price(row.get("price_in"))
    price_out = _price(row.get("price_out"))
    if price_in is not None:
        public["price_in"] = price_in
    if price_out is not None:
        public["price_out"] = price_out
    released_at = row.get("released_at")
    if isinstance(released_at, int) and not isinstance(released_at, bool) and released_at > 0:
        public["released_at"] = released_at
    return public


def _provider_secret(config_path: Path | None, name: str) -> str:
    config = load_config(config_path) if config_path is not None else load_config()
    resolved = resolve_settings_provider(config, name)
    if resolved is None:
        return ""
    secret = resolved[2].api_key
    return secret if isinstance(secret, str) else ""


def provider_models_document(
    name: str,
    *,
    config_path: Path | None = None,
    query: str = "",
) -> dict[str, Any]:
    """Model catalog for one provider, including the models selected for the agent."""
    provider = _checked_name(name)
    try:
        payload = provider_models_payload({"provider": [provider]}, config_path=config_path)
    except MokliSettingsError as exc:
        raise _settings_error(exc) from exc
    config = load_config(config_path) if config_path is not None else load_config()
    selection = provider_model_selection(config, provider)
    needle = query.strip().casefold()
    models: list[dict[str, Any]] = []
    raw_models = payload.get("models")
    if isinstance(raw_models, list):
        for row in raw_models:
            if not isinstance(row, dict):
                continue
            public = _public_model(row)
            if public is None:
                continue
            if needle:
                label = public.get("label")
                haystack = public["id"].casefold()
                if isinstance(label, str):
                    haystack = f"{haystack} {label.casefold()}"
                if needle not in haystack:
                    continue
            models.append(public)
    count = payload.get("model_count")
    message = payload.get("message")
    document = {
        "provider": payload.get("provider", provider),
        "status": payload.get("status"),
        "catalog_kind": payload.get("catalog_kind"),
        "models": models,
        "model_count": count if isinstance(count, int) else len(models),
        "message": message if isinstance(message, str) else None,
        "selected": selection["selected"],
        "primary": selection["primary"],
    }
    return _guard(document, [_provider_secret(config_path, provider)])


def save_provider_models(
    name: str,
    body: JsonObject,
    *,
    config_path: Path | None,
) -> dict[str, Any]:
    """Persist one or more models from this provider as the agent call order."""
    provider = _checked_name(name)
    raw_models = body.get("models")
    if not isinstance(raw_models, list):
        raise ApiError(400, "invalid_field", details={"field": "models"})
    model_ids: list[str] = []
    for item in raw_models:
        if not isinstance(item, str):
            raise ApiError(400, "invalid_field", details={"field": "models"})
        model_ids.append(item)
    primary = body.get("primary")
    if primary is not None and not isinstance(primary, str):
        raise ApiError(400, "invalid_field", details={"field": "primary"})
    windows: dict[str, int] = {}
    raw_windows = body.get("context_windows")
    if raw_windows is not None:
        if not isinstance(raw_windows, dict):
            raise ApiError(400, "invalid_field", details={"field": "context_windows"})
        for key, value in raw_windows.items():
            if (
                isinstance(key, str)
                and isinstance(value, int)
                and not isinstance(value, bool)
                and 0 < value <= 10_000_000
            ):
                windows[key] = value

    def _save(path: Path | None) -> None:
        config = load_config(path) if path is not None else load_config()
        try:
            assign_provider_models(
                config,
                provider,
                model_ids,
                primary_model=primary if isinstance(primary, str) and primary.strip() else None,
                oauth_status=oauth_provider_status,
                context_windows=windows,
            )
        except MokliSettingsError as exc:
            raise _settings_error(exc) from exc
        if path is None:
            save_config(config)
        else:
            save_config(config, path)

    _locked(config_path, _save)
    refresh_bound_runtime()
    config = load_config(config_path) if config_path is not None else load_config()
    selection = provider_model_selection(config, provider)
    return _guard(
        {"provider": provider, "selected": selection["selected"], "primary": selection["primary"]},
        [_provider_secret(config_path, provider)],
    )


def _selection_fields(config: Config, name: str) -> dict[str, Any]:
    selection = provider_model_selection(config, name)
    raw = selection.get("selected")
    chosen: list[str] = []
    if isinstance(raw, list):
        for entry in cast(list[object], raw):
            if isinstance(entry, str) and entry not in chosen:
                chosen.append(entry)
            if len(chosen) == 12:
                break
    fields: dict[str, Any] = {"selected_models": chosen}
    primary = selection.get("primary")
    if isinstance(primary, str) and primary:
        fields["primary_model"] = primary
    return fields


def provider_document(config_path: Path | None = None) -> dict[str, Any]:
    """Configured and available providers. No API keys and no OAuth token."""
    config = load_config(config_path) if config_path is not None else load_config()
    payload = model_settings_payload(config, oauth_status=oauth_provider_status)
    rows = payload.get("providers")
    providers: list[dict[str, Any]] = []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            public = _public_row(row)
            name = public.get("name")
            if isinstance(name, str):
                public.update(_selection_fields(config, name))
            providers.append(public)
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
        except MokliSettingsError as exc:
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
        except MokliSettingsError as exc:
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
    except MokliSettingsError as exc:
        raise _settings_error(exc, token or None) from exc
    refresh_bound_runtime()
    return _guard(provider_document(config_path), [] if clear else [token])


def claude_connect(flows: MokliOAuthFlowRegistry) -> dict[str, Any]:
    started = start_connect_payload(flows)
    return {key: started[key] for key in _FLOW_FIELDS if key in started}


def claude_callback(
    body: JsonObject,
    flows: MokliOAuthFlowRegistry,
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
    except MokliSettingsError as exc:
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
    flows: MokliOAuthFlowRegistry,
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
        except MokliSettingsError as exc:
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
