"""Codex device-code login never uses the phone's localhost callback."""

from __future__ import annotations

import base64
import json

import httpx
import pytest

from nanobot.providers.openai_codex_device import (
    CodexDeviceError,
    start_openai_codex_device_login,
)


def _jwt(account_id: str) -> str:
    def encode(value: object) -> str:
        raw = json.dumps(value).encode("utf-8")
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

    payload = {"https://api.openai.com/auth": {"chatgpt_account_id": account_id}}
    return f"{encode({'alg': 'none'})}.{encode(payload)}."


class _Response:
    def __init__(self, status: int, payload: object) -> None:
        self.status_code = status
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self) -> object:
        return self._payload


class _Client:
    def __init__(self, script: list[tuple[int, object]]) -> None:
        self._script = script
        self.urls: list[str] = []

    def __enter__(self) -> _Client:
        return self

    def __exit__(self, *_args: object) -> bool:
        return False

    def post(self, url: str, **_kwargs: object) -> _Response:
        self.urls.append(url)
        status, payload = self._script.pop(0)
        return _Response(status, payload)


def test_device_login_waits_then_saves_without_localhost(
    tmp_path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    token_path = tmp_path / "codex.json"
    monkeypatch.setenv("OAUTH_CLI_KIT_TOKEN_PATH", str(token_path))
    access = _jwt("acct_test")
    script = [
        (200, {"device_auth_id": "device-secret", "user_code": "ABCD-EFGH", "interval": "5"}),
        (404, {"error": "authorization_pending"}),
        (
            200,
            {
                "authorization_code": "auth-code-secret",
                "code_verifier": "verifier-secret",
                "code_challenge": "challenge",
            },
        ),
        (
            200,
            {"access_token": access, "refresh_token": "refresh-secret", "expires_in": 3600},
        ),
    ]
    clients: list[_Client] = []

    def fake_client(*_args, **_kwargs) -> _Client:
        client = _Client(script)
        clients.append(client)
        return client

    monkeypatch.setattr("nanobot.providers.openai_codex_device.httpx.Client", fake_client)

    flow = start_openai_codex_device_login(timeout_s=30)
    assert flow.authorization_url == "https://auth.openai.com/codex/device"
    assert flow.user_code == "ABCD-EFGH"
    assert "localhost" not in flow.authorization_url
    assert flow.poll() is None
    token = flow.poll()

    assert token is not None
    assert token.account_id == "acct_test"
    stored = json.loads(token_path.read_text(encoding="utf-8"))
    assert stored["access"] == access
    public = f"{flow.authorization_url} {flow.user_code}"
    assert "device-secret" not in public
    assert access not in public
    assert "refresh-secret" not in public
    assert all("localhost" not in url for client in clients for url in client.urls)


def test_device_login_error_hides_the_response_body(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "token-body-secret"

    class Broken(_Client):
        def __init__(self) -> None:
            super().__init__([(502, {"access_token": secret})])

    monkeypatch.setattr(
        "nanobot.providers.openai_codex_device.httpx.Client",
        lambda *_args, **_kwargs: Broken(),
    )

    with pytest.raises(CodexDeviceError) as exc:
        start_openai_codex_device_login()

    assert secret not in str(exc.value)
    assert "502" in str(exc.value)


def test_device_login_network_error_has_no_url_details(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(*_args, **_kwargs):
        raise httpx.ConnectError("proxy secret.example")

    monkeypatch.setattr("nanobot.providers.openai_codex_device.httpx.Client", broken)

    with pytest.raises(CodexDeviceError) as exc:
        start_openai_codex_device_login()

    assert "secret.example" not in str(exc.value)
