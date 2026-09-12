"""Claude Code CLI OAuth token settings: persist, mask, auth."""

from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from websockets.datastructures import Headers

from nanobot.config.loader import get_config_path
from nanobot.webui.claude_code_oauth import (
    ENV_KEY,
    apply_claude_code_oauth_token,
    mask_token_last4,
    public_status,
    resolve_env_file_path,
)
from nanobot.webui.http_utils import http_json_response
from nanobot.webui.settings_api import settings_payload, update_claude_code_oauth_settings
from nanobot.webui.settings_contracts import WebUISettingsError
from nanobot.webui.settings_routes import WebUISettingsRouter
from nanobot.webui.settings_services import WebUISettingsServices


def _router(*, authorized: bool = True, config_path: Path | None = None) -> WebUISettingsRouter:
    return WebUISettingsRouter(
        settings=WebUISettingsServices.create(config_path or get_config_path()),
        bus=SimpleNamespace(),
        logger=SimpleNamespace(exception=lambda *_args: None),
        check_api_token=lambda _request: authorized,
        parse_query=lambda path: {},
        json_response=http_json_response,
        error_response=lambda status, message: http_json_response(
            {"error": message},
            status=status,
        ),
        runtime_surface="browser",
        runtime_capabilities={},
    )


def _mutation_request(path: str, payload: dict[str, object]) -> SimpleNamespace:
    request = SimpleNamespace(path=path, headers=Headers())
    request._nanobot_webui_mutation_request = True
    request._nanobot_webui_mutation_payload = payload
    request._nanobot_trusted_proxy_authenticated = True
    return request


@pytest.fixture
def isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    env_file = tmp_path / ".env"
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("NANOAGENT_ENV_FILE", str(env_file))
    monkeypatch.delenv(ENV_KEY, raising=False)
    return env_file


def test_mask_token_last4_never_returns_full_secret() -> None:
    secret = "sk-ant-oat-abcdefghijklmnop"
    hint = mask_token_last4(secret)
    assert hint == "••••mnop"
    assert secret not in (hint or "")
    assert mask_token_last4("abcd") == "••••"
    assert mask_token_last4("") is None
    assert mask_token_last4(None) is None


def test_resolve_env_file_prefers_override_then_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    override = tmp_path / "custom.env"
    monkeypatch.setenv("NANOAGENT_ENV_FILE", str(override))
    assert resolve_env_file_path() == override
    monkeypatch.delenv("NANOAGENT_ENV_FILE")
    monkeypatch.setenv("HOME", str(tmp_path))
    assert resolve_env_file_path() == tmp_path / ".env"


def test_apply_persists_mode_0600_updates_process_env_and_preserves_other_keys(
    isolated_env: Path,
) -> None:
    isolated_env.write_text("OANDA_API_TOKEN=keep-me\nNANOAGENT_WEB_TOKEN=bootstrap\n")
    token = "  setup-token-value-xyz9  "
    status = apply_claude_code_oauth_token(token)

    assert status["configured"] is True
    assert status["hint"] == "••••xyz9"
    assert status["env_key"] == ENV_KEY
    assert token.strip() not in json.dumps(status)
    assert os.environ[ENV_KEY] == "setup-token-value-xyz9"

    text = isolated_env.read_text(encoding="utf-8")
    assert "OANDA_API_TOKEN=keep-me" in text
    assert "NANOAGENT_WEB_TOKEN=bootstrap" in text
    assert "setup-token-value-xyz9" in text
    mode = isolated_env.stat().st_mode & 0o777
    assert mode == 0o600


def test_apply_rejects_empty_and_whitespace(isolated_env: Path) -> None:
    with pytest.raises(WebUISettingsError, match="required"):
        apply_claude_code_oauth_token("")
    with pytest.raises(WebUISettingsError, match="required"):
        apply_claude_code_oauth_token("   ")
    assert not isolated_env.exists()
    assert ENV_KEY not in os.environ


def test_apply_clear_removes_token_and_preserves_other_keys(isolated_env: Path) -> None:
    isolated_env.write_text("OANDA_API_TOKEN=keep-me\n")
    apply_claude_code_oauth_token("setup-token-value-abcd")
    status = apply_claude_code_oauth_token(None)
    assert status["configured"] is False
    assert status["hint"] is None
    assert ENV_KEY not in os.environ
    text = isolated_env.read_text(encoding="utf-8")
    assert "CLAUDE_CODE_OAUTH_TOKEN" not in text
    assert "OANDA_API_TOKEN=keep-me" in text


def test_update_settings_returns_masked_payload(
    isolated_env: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nanobot.config.schema import Config

    config_path = tmp_path / "config.json"
    config_path.write_text("{}\n")
    monkeypatch.setattr(
        "nanobot.webui.settings_api._load_settings_config",
        lambda _path=None: Config(),
    )
    token = "operator-setup-token-QQ99"
    payload = update_claude_code_oauth_settings(
        {"token": [f"  {token}  "]},
        config_path=config_path,
    )
    dumped = json.dumps(payload)
    assert token not in dumped
    assert payload["claude_code_oauth"]["configured"] is True
    assert payload["claude_code_oauth"]["hint"] == "••••QQ99"
    row = next(item for item in payload["providers"] if item["name"] == "claude_code_cli")
    assert row["configured"] is True
    assert row["auth_type"] == "cli_oauth"
    assert row["cli_oauth_hint"] == "••••QQ99"
    assert row.get("api_key_hint") in {None, "••••"}


def test_settings_payload_status_does_not_echo_token(
    isolated_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nanobot.config.schema import Config

    os.environ[ENV_KEY] = "live-process-token-zz42"
    monkeypatch.setattr(
        "nanobot.webui.settings_api._load_settings_config",
        lambda _path=None: Config(),
    )
    payload = settings_payload()
    dumped = json.dumps(payload)
    assert "live-process-token-zz42" not in dumped
    assert payload["claude_code_oauth"] == public_status()
    assert payload["claude_code_oauth"]["hint"] == "••••zz42"


def test_update_does_not_log_token_value(
    isolated_env: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret = "must-not-appear-in-logs-7788"
    with caplog.at_level("DEBUG"):
        apply_claude_code_oauth_token(secret)
    combined = caplog.text
    assert secret not in combined
    assert "7788" not in combined


@pytest.mark.asyncio
async def test_route_persists_and_masks(
    isolated_env: Path,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}\n")
    token = "route-setup-token-AB12"
    request = _mutation_request("/api/settings/claude-code-oauth", {"token": token})
    response = await _router(config_path=config_path).dispatch(
        None,
        request,
        "/api/settings/claude-code-oauth",
    )
    assert response is not None
    assert response.status_code == 200
    payload = json.loads(response.body)
    assert token not in response.body.decode("utf-8")
    assert payload["claude_code_oauth"]["configured"] is True
    assert payload["claude_code_oauth"]["hint"] == "••••AB12"
    assert os.environ[ENV_KEY] == token
    assert ENV_KEY in isolated_env.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_route_rejects_unauthenticated(isolated_env: Path, tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}\n")
    token = "should-not-be-saved-9911"
    request = _mutation_request("/api/settings/claude-code-oauth", {"token": token})
    response = await _router(authorized=False, config_path=config_path).dispatch(
        None,
        request,
        "/api/settings/claude-code-oauth",
    )
    assert response is not None
    assert response.status_code == 401
    assert token not in response.body.decode("utf-8")
    assert ENV_KEY not in os.environ
    assert not isolated_env.exists() or ENV_KEY not in isolated_env.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_route_rejects_empty_token(isolated_env: Path, tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}\n")
    request = _mutation_request("/api/settings/claude-code-oauth", {"token": "   "})
    response = await _router(config_path=config_path).dispatch(
        None,
        request,
        "/api/settings/claude-code-oauth",
    )
    assert response is not None
    assert response.status_code == 400
    assert json.loads(response.body)["error"] == "Claude Code CLI token is required"


@pytest.mark.asyncio
async def test_route_clear_token(isolated_env: Path, tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}\n")
    apply_claude_code_oauth_token("clear-me-token-3344")
    request = _mutation_request("/api/settings/claude-code-oauth", {"clear": True})
    response = await _router(config_path=config_path).dispatch(
        None,
        request,
        "/api/settings/claude-code-oauth",
    )
    assert response is not None
    assert response.status_code == 200
    payload = json.loads(response.body)
    assert payload["claude_code_oauth"]["configured"] is False
    assert ENV_KEY not in os.environ
    assert "clear-me-token-3344" not in response.body.decode("utf-8")
