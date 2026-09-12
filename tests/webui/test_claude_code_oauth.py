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
from nanobot.webui.claude_code_oauth_flow import (
    create_connect_flow,
    exchange_authorization_code,
    parse_authorization_response,
    token_url,
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


def test_parse_authorization_response_accepts_code_hash_state() -> None:
    code, state = parse_authorization_response("  auth-code-value#csrf-state-1  ")
    assert code == "auth-code-value"
    assert state == "csrf-state-1"
    code, state = parse_authorization_response(
        "https://platform.claude.com/oauth/code/callback?code=from-url&state=url-state"
    )
    assert code == "from-url"
    assert state == "url-state"
    with pytest.raises(WebUISettingsError, match="state"):
        parse_authorization_response("only-a-code")
    code, state = parse_authorization_response(
        "https://platform.claude.com/oauth/code/callback#frag-code#frag-state"
    )
    assert code == "frag-code"
    assert state == "frag-state"
    with pytest.raises(WebUISettingsError, match="code"):
        parse_authorization_response("   ")


def test_connect_flow_cancel_and_token_url_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    flow = create_connect_flow(timeout_s=30)
    assert flow.remaining_seconds > 0
    flow.cancel()
    assert flow.expired is True
    assert flow.remaining_seconds == 0
    monkeypatch.setenv("NANOAGENT_CLAUDE_OAUTH_TOKEN_URL", "https://oauth.test/token")
    assert token_url() == "https://oauth.test/token"


def test_exchange_authorization_code_uses_post_fn_and_hides_secrets() -> None:
    class _Response:
        status_code = 200

        def json(self) -> dict[str, str]:
            return {"access_token": "sk-ant-oat-exchanged-4411"}

    captured: dict[str, object] = {}

    def post_fn(url: str, payload: dict[str, str]) -> _Response:
        captured["url"] = url
        captured["payload"] = payload
        return _Response()

    token = exchange_authorization_code(
        code="auth-code",
        state="csrf-state",
        code_verifier="verifier-secret",
        post_fn=post_fn,
    )
    assert token == "sk-ant-oat-exchanged-4411"
    assert captured["payload"]["code_verifier"] == "verifier-secret"
    assert captured["payload"]["grant_type"] == "authorization_code"

    class _Bad:
        status_code = 400

        def json(self) -> dict[str, str]:
            return {"error": "invalid_grant"}

    with pytest.raises(WebUISettingsError, match="failed"):
        exchange_authorization_code(
            code="auth-code",
            state="csrf-state",
            code_verifier="verifier-secret",
            post_fn=lambda _url, _payload: _Bad(),
        )
    with pytest.raises(WebUISettingsError, match="failed"):
        exchange_authorization_code(
            code="auth-code",
            state="csrf-state",
            code_verifier="verifier-secret",
            post_fn=lambda _url, _payload: (_ for _ in ()).throw(RuntimeError("boom")),
        )


@pytest.mark.asyncio
async def test_callback_accepts_state_without_flow_id(
    isolated_env: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}\n")
    router = _router(config_path=config_path)
    start = await router.dispatch(
        None,
        _mutation_request("/api/settings/claude-code-oauth/connect", {}),
        "/api/settings/claude-code-oauth/connect",
    )
    assert start is not None
    flow = json.loads(start.body)
    from urllib.parse import parse_qs, urlsplit

    state = parse_qs(urlsplit(flow["authorization_url"]).query)["state"][0]
    token = "sk-ant-oat-state-only-7788"
    monkeypatch.setattr(
        "nanobot.webui.claude_code_oauth_flow.exchange_authorization_code",
        lambda **_kwargs: token,
    )
    response = await router.dispatch(
        None,
        _mutation_request(
            "/api/settings/claude-code-oauth/callback",
            {"code": "auth-code-value", "state": state},
        ),
        "/api/settings/claude-code-oauth/callback",
    )
    assert response is not None
    assert response.status_code == 200
    payload = json.loads(response.body)
    assert token not in response.body.decode("utf-8")
    assert payload["claude_code_oauth"]["hint"] == "••••7788"
    assert os.environ[ENV_KEY] == token


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
    monkeypatch.delenv("HOME")
    assert resolve_env_file_path() == Path(".env")


def test_upsert_replaces_existing_and_export_lines(isolated_env: Path) -> None:
    isolated_env.write_text(
        "export CLAUDE_CODE_OAUTH_TOKEN=old-token-0000\nOANDA_API_TOKEN=keep-me\n"
    )
    apply_claude_code_oauth_token("new-token-value-1111")
    text = isolated_env.read_text(encoding="utf-8")
    assert "old-token-0000" not in text
    assert "new-token-value-1111" in text
    assert text.count("CLAUDE_CODE_OAUTH_TOKEN=") == 1
    assert "OANDA_API_TOKEN=keep-me" in text


def test_upsert_cleans_tempfile_when_replace_fails(
    isolated_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    isolated_env.write_text("OANDA_API_TOKEN=keep-me\n")

    def boom(src: str, dst: str) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError, match="replace failed"):
        apply_claude_code_oauth_token("temp-cleanup-token-2222")
    leftovers = list(isolated_env.parent.glob(".env.*.tmp"))
    assert leftovers == []
    assert ENV_KEY not in isolated_env.read_text(encoding="utf-8")
    assert ENV_KEY not in os.environ


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


def _parse_auth_url(url: str) -> dict[str, list[str]]:
    from urllib.parse import parse_qs, urlsplit

    return parse_qs(urlsplit(url).query)


@pytest.mark.asyncio
async def test_connect_requires_auth(isolated_env: Path, tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}\n")
    request = _mutation_request("/api/settings/claude-code-oauth/connect", {})
    response = await _router(authorized=False, config_path=config_path).dispatch(
        None,
        request,
        "/api/settings/claude-code-oauth/connect",
    )
    assert response is not None
    assert response.status_code == 401
    assert ENV_KEY not in os.environ


@pytest.mark.asyncio
async def test_connect_returns_official_authorize_url(
    isolated_env: Path,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}\n")
    request = _mutation_request("/api/settings/claude-code-oauth/connect", {})
    response = await _router(config_path=config_path).dispatch(
        None,
        request,
        "/api/settings/claude-code-oauth/connect",
    )
    assert response is not None
    assert response.status_code == 200
    payload = json.loads(response.body)
    assert payload["status"] == "authorization_required"
    assert payload["provider"] == "claude_code_cli"
    assert payload["completion_input"] == "authorization_code"
    assert payload["flow_id"]
    url = payload["authorization_url"]
    assert url.startswith("https://claude.com/cai/oauth/authorize?")
    params = _parse_auth_url(url)
    assert params["client_id"] == ["9d1c250a-e61b-44d9-88ed-5944d1962f5e"]
    assert params["response_type"] == ["code"]
    assert params["code"] == ["true"]
    assert params["code_challenge_method"] == ["S256"]
    assert params["scope"] == ["user:inference"]
    assert params["redirect_uri"] == ["https://platform.claude.com/oauth/code/callback"]
    assert params["state"][0]
    assert params["code_challenge"][0]
    dumped = response.body.decode("utf-8")
    assert "code_verifier" not in dumped
    assert ENV_KEY not in dumped


@pytest.mark.asyncio
async def test_callback_requires_auth(
    isolated_env: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}\n")
    token = "must-not-persist-unauth-9911"
    monkeypatch.setattr(
        "nanobot.webui.claude_code_oauth_flow.exchange_authorization_code",
        lambda **_kwargs: token,
    )
    request = _mutation_request(
        "/api/settings/claude-code-oauth/callback",
        {"code": "auth-code", "state": "bad-state"},
    )
    response = await _router(authorized=False, config_path=config_path).dispatch(
        None,
        request,
        "/api/settings/claude-code-oauth/callback",
    )
    assert response is not None
    assert response.status_code == 401
    assert token not in response.body.decode("utf-8")
    assert ENV_KEY not in os.environ
    assert not isolated_env.exists() or ENV_KEY not in isolated_env.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_callback_rejects_bad_state_csrf(
    isolated_env: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}\n")
    router = _router(config_path=config_path)
    start = await router.dispatch(
        None,
        _mutation_request("/api/settings/claude-code-oauth/connect", {}),
        "/api/settings/claude-code-oauth/connect",
    )
    assert start is not None
    flow = json.loads(start.body)
    exchanged = {"called": False}

    def boom(**_kwargs: object) -> str:
        exchanged["called"] = True
        return "should-not-exchange-csrf"

    monkeypatch.setattr(
        "nanobot.webui.claude_code_oauth_flow.exchange_authorization_code",
        boom,
    )
    response = await router.dispatch(
        None,
        _mutation_request(
            "/api/settings/claude-code-oauth/callback",
            {
                "flow_id": flow["flow_id"],
                "code": "auth-code-value",
                "state": "forged-state-value",
            },
        ),
        "/api/settings/claude-code-oauth/callback",
    )
    assert response is not None
    assert response.status_code == 400
    assert json.loads(response.body)["error"] == "Invalid or expired Claude sign-in state."
    assert exchanged["called"] is False
    assert ENV_KEY not in os.environ


@pytest.mark.asyncio
async def test_callback_stores_masked_token(
    isolated_env: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}\n")
    router = _router(config_path=config_path)
    start = await router.dispatch(
        None,
        _mutation_request("/api/settings/claude-code-oauth/connect", {}),
        "/api/settings/claude-code-oauth/connect",
    )
    assert start is not None
    flow = json.loads(start.body)
    from urllib.parse import parse_qs, urlsplit

    state = parse_qs(urlsplit(flow["authorization_url"]).query)["state"][0]
    token = "sk-ant-oat-connect-ZZ99"
    monkeypatch.setattr(
        "nanobot.webui.claude_code_oauth_flow.exchange_authorization_code",
        lambda **_kwargs: token,
    )
    response = await router.dispatch(
        None,
        _mutation_request(
            "/api/settings/claude-code-oauth/callback",
            {
                "flow_id": flow["flow_id"],
                "authorization_response": f"auth-code-value#{state}",
            },
        ),
        "/api/settings/claude-code-oauth/callback",
    )
    assert response is not None
    assert response.status_code == 200
    payload = json.loads(response.body)
    dumped = response.body.decode("utf-8")
    assert token not in dumped
    assert "auth-code-value" not in dumped
    assert payload["claude_code_oauth"]["configured"] is True
    assert payload["claude_code_oauth"]["hint"] == "••••ZZ99"
    row = next(item for item in payload["providers"] if item["name"] == "claude_code_cli")
    assert row["configured"] is True
    assert row["cli_oauth_hint"] == "••••ZZ99"
    assert os.environ[ENV_KEY] == token
    assert ENV_KEY in isolated_env.read_text(encoding="utf-8")
    assert isolated_env.stat().st_mode & 0o777 == 0o600
