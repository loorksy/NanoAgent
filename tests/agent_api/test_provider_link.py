"""Provider linking keeps API keys and the Claude Code token off the wire."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx
from aiohttp.test_utils import TestClient

from agent_api.conftest import auth
from nanobot.agent_api.context import SERVICES_KEY


def _wire(body: object) -> str:
    return json.dumps(body)


async def test_provider_key_is_saved_and_not_echoed(
    client: TestClient, tmp_path: Path,
) -> None:
    secret = "sk-live-openrouter-test-KEY99"
    saved = await client.put(
        "/api/v2/settings/providers/openrouter",
        headers=auth(),
        json={"api_key": secret, "api_base": "https://openrouter.ai/api/v1"},
    )
    assert saved.status == 200
    body = await saved.json()
    assert secret not in _wire(body)
    row = next(item for item in body["providers"] if item["name"] == "openrouter")
    assert row["configured"] is True
    assert row["api_key_hint"]
    assert secret not in row["api_key_hint"]
    stored = (tmp_path / "config.json").read_text(encoding="utf-8")
    assert secret in stored


async def test_custom_provider_is_created_without_echoing_the_key(
    client: TestClient,
) -> None:
    secret = "custom-provider-secret-KEY88"
    created = await client.post(
        "/api/v2/settings/providers",
        headers=auth(),
        json={
            "name": "My Relay",
            "api_base": "https://relay.example/v1",
            "api_key": secret,
        },
    )
    assert created.status == 200
    body = await created.json()
    assert secret not in _wire(body)
    key = body["created_provider"]
    row = next(item for item in body["providers"] if item["name"] == key)
    assert row["is_custom"] is True
    assert row["configured"] is True
    assert row["api_base"] == "https://relay.example/v1"


async def test_read_scope_cannot_save_a_provider(client: TestClient) -> None:
    issued = client.app[SERVICES_KEY].tokens.issue("service", scopes=["read"], label="reader")
    denied = await client.post(
        "/api/v2/settings/claude-code",
        headers=auth(issued["token"]),
        json={"token": "should-not-save"},
    )
    assert denied.status == 403


async def test_claude_token_round_trip_never_echoes_the_secret(
    client: TestClient, monkeypatch, tmp_path: Path,
) -> None:
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    env_file = tmp_path / "service.env"
    monkeypatch.setenv("NANOAGENT_ENV_FILE", str(env_file))
    token = "sk-ant-oat01-claude-code-secret-IkOw"

    saved = await client.post(
        "/api/v2/settings/claude-code",
        headers=auth(),
        json={"token": token},
    )
    assert saved.status == 200
    body = await saved.json()
    encoded = _wire(body)
    assert token not in encoded
    assert "code_verifier" not in encoded
    claude = next(item for item in body["providers"] if item["name"] == "claude_code_cli")
    assert claude["configured"] is True
    assert claude["auth_type"] == "cli_oauth"
    assert claude["cli_oauth_hint"] == "••••IkOw"
    assert token in env_file.read_text(encoding="utf-8")

    cleared = await client.post(
        "/api/v2/settings/claude-code",
        headers=auth(),
        json={"clear": True},
    )
    assert cleared.status == 200
    cleared_body = await cleared.json()
    assert token not in _wire(cleared_body)
    row = next(item for item in cleared_body["providers"] if item["name"] == "claude_code_cli")
    assert row["configured"] is False
    assert "CLAUDE_CODE_OAUTH_TOKEN" not in env_file.read_text(encoding="utf-8")


async def test_claude_connect_exchanges_without_returning_the_token(
    client: TestClient, monkeypatch, tmp_path: Path,
) -> None:
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    monkeypatch.setenv("NANOAGENT_ENV_FILE", str(tmp_path / "oauth.env"))
    exchanged = "exchanged-claude-token-value-ZZZZ"

    def _exchange(**_kwargs: object) -> str:
        return exchanged

    monkeypatch.setattr(
        "nanobot.webui.claude_code_oauth_flow.exchange_authorization_code",
        _exchange,
    )
    started = await client.post("/api/v2/settings/claude-code/connect", headers=auth(), json={})
    assert started.status == 200
    flow = await started.json()
    assert flow["status"] == "authorization_required"
    assert flow["provider"] == "claude_code_cli"
    assert "code_verifier" not in _wire(flow)
    assert exchanged not in _wire(flow)
    state = parse_qs(urlsplit(flow["authorization_url"]).query)["state"][0]

    finished = await client.post(
        "/api/v2/settings/claude-code/callback",
        headers=auth(),
        json={"flow_id": flow["flow_id"], "code": "auth-code", "state": state},
    )
    assert finished.status == 200
    body = await finished.json()
    assert exchanged not in _wire(body)
    assert "auth-code" not in _wire(body)
    claude = next(item for item in body["providers"] if item["name"] == "claude_code_cli")
    assert claude["cli_oauth_hint"] == "••••ZZZZ"


async def test_provider_model_selection_hides_the_api_key(
    client: TestClient, agent, monkeypatch,
) -> None:
    secret = "sk-or-v1-catalog-secret-KEY77"
    saved = await client.put(
        "/api/v2/settings/providers/openrouter",
        headers=auth(),
        json={"api_key": secret},
    )
    assert saved.status == 200

    def fake_get(url: str, **kwargs):
        assert kwargs["headers"]["Authorization"] == f"Bearer {secret}"
        assert url == "https://openrouter.ai/api/v1/models"
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": "google/gemini-test",
                        "name": "Gemini Test",
                        "context_length": 1_300_000,
                        "created": 1787702400,
                        "architecture": {
                            "input_modalities": ["text", "image", "video"],
                            "output_modalities": ["text"],
                        },
                        "pricing": {"prompt": "0.00000004", "completion": "0.0000005"},
                    }
                ]
            },
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr("nanobot.webui.settings_api.httpx.get", fake_get)
    listed = await client.get("/api/v2/settings/providers/openrouter/models", headers=auth())
    assert listed.status == 200
    catalog = await listed.json()
    assert secret not in _wire(catalog)
    assert catalog["models"][0]["price_in"] == 0.04
    assert catalog["models"][0]["input_modalities"] == ["text", "image", "video"]
    assert catalog["models"][0]["context_window"] == 1_300_000

    chosen = await client.put(
        "/api/v2/settings/providers/openrouter/models",
        headers=auth(),
        json={
            "models": ["google/gemini-test"],
            "primary": "google/gemini-test",
            "context_windows": {"google/gemini-test": 1_300_000},
        },
    )
    assert chosen.status == 200
    body = await chosen.json()
    assert secret not in _wire(body)
    assert body["selected"] == ["google/gemini-test"]
    assert body["primary"] == "google/gemini-test"

    listed_providers = await client.get("/api/v2/settings/providers", headers=auth())
    assert listed_providers.status == 200
    providers = await listed_providers.json()
    row = next(item for item in providers["providers"] if item["name"] == "openrouter")
    assert row["selected_models"] == ["google/gemini-test"]
    assert row["primary_model"] == "google/gemini-test"
    assert secret not in _wire(providers)

    catalog = await client.get("/api/v2/chat/models", headers=auth())
    assert catalog.status == 200
    chat_models = await catalog.json()
    assert chat_models["models"] == [
        {"id": "google/gemini-test", "name": "google/gemini-test"},
    ]
    assert secret not in _wire(chat_models)

    sent = await client.post(
        "/api/v2/sessions/chat-models/messages",
        headers=auth(),
        json={"content": "hi", "model": "google/gemini-test"},
    )
    assert sent.status == 202
    assert agent.presets == [("agent_api:chat-models", "gemini-test")]

    prefixed = await client.post(
        "/api/v2/sessions/chat-models/messages",
        headers=auth(),
        json={"content": "hi", "model": "nanoagent.google/gemini-test"},
    )
    assert prefixed.status == 202
    assert agent.presets[-1] == ("agent_api:chat-models", "gemini-test")

    cleared = await client.post(
        "/api/v2/sessions/chat-models/messages",
        headers=auth(),
        json={"content": "hi", "model": None},
    )
    assert cleared.status == 202
    assert agent.cleared == ["agent_api:chat-models"]

    unknown = await client.post(
        "/api/v2/sessions/chat-models/messages",
        headers=auth(),
        json={"content": "hi", "model": "other/not-selected"},
    )
    assert unknown.status == 400

    listed = await (await client.get("/v1/models", headers=auth())).json()
    assert [row["id"] for row in listed["data"]] == ["nanoagent", "google/gemini-test"]
    compat = await client.post(
        "/v1/chat/completions",
        headers={**auth(), "X-OpenWebUI-Chat-Id": "chat-42"},
        json={
            "model": "google/gemini-test",
            "messages": [{"role": "user", "content": "hi"}],
        },
    )
    assert compat.status == 200
    compat_body = await compat.json()
    assert compat_body["model"] == "google/gemini-test"
    assert ("api:chat-42", "gemini-test") in agent.presets
    rejected = await client.post(
        "/v1/chat/completions",
        headers=auth(),
        json={"model": "other/not-selected", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert rejected.status == 400

    issued = client.app[SERVICES_KEY].tokens.issue("service", scopes=["read"], label="reader")
    denied = await client.put(
        "/api/v2/settings/providers/openrouter/models",
        headers=auth(issued["token"]),
        json={"models": ["google/gemini-test"]},
    )
    assert denied.status == 403
