"""Phone-friendly OpenAI Codex login.

The browser callback is fixed to ``http://localhost:1455``. A phone cannot
reach that address, so remote sign-in uses Codex device-code login: the
person opens ``https://auth.openai.com/codex/device`` and types a short code.
"""

# oauth-cli-kit does not publish type stubs.
# pyright: reportMissingTypeStubs=false

from __future__ import annotations

import base64
import json
import threading
import time
from typing import Any, cast

import httpx
from oauth_cli_kit.models import OAuthToken
from oauth_cli_kit.providers import OPENAI_CODEX_PROVIDER
from oauth_cli_kit.storage import FileTokenStorage

_ISSUER = "https://auth.openai.com"
_USER_CODE_URL = f"{_ISSUER}/api/accounts/deviceauth/usercode"
_TOKEN_POLL_URL = f"{_ISSUER}/api/accounts/deviceauth/token"
_DEVICE_REDIRECT = f"{_ISSUER}/deviceauth/callback"
_PENDING = {403, 404}


class CodexDeviceError(RuntimeError):
    """A device-code failure that contains no credential material."""


class CodexDeviceUnavailableError(CodexDeviceError):
    """Device-code login is not offered, so the caller may use another flow."""


class CodexDeviceLogin:
    """One device-code attempt. The device id stays on the server."""

    def __init__(
        self,
        *,
        device_auth_id: str,
        user_code: str,
        proxy: str | None,
        timeout_s: float,
    ) -> None:
        self.authorization_url = f"{_ISSUER}/codex/device"
        self.user_code = user_code
        self._device_auth_id = device_auth_id
        self._proxy = proxy
        self._expires_at = time.monotonic() + timeout_s
        self._lock = threading.Lock()
        self._cancelled = False
        self._finished = False

    @property
    def expired(self) -> bool:
        return self._cancelled or time.monotonic() >= self._expires_at

    @property
    def remaining_seconds(self) -> int:
        return max(0, int(self._expires_at - time.monotonic()))

    def cancel(self) -> None:
        self._cancelled = True

    def poll(self) -> OAuthToken | None:
        """Return the saved token, or ``None`` while OpenAI is still waiting."""
        if self._finished:
            raise CodexDeviceError("OpenAI Codex sign-in already finished.")
        if self.expired:
            raise CodexDeviceError("OpenAI Codex sign-in expired. Start again.")
        with self._lock:
            if self._finished or self.expired:
                raise CodexDeviceError("OpenAI Codex sign-in expired. Start again.")
            issued = _poll_once(self._device_auth_id, self.user_code, self._proxy)
            if issued is None:
                return None
            token = _exchange(issued, self._proxy)
            FileTokenStorage(token_filename=OPENAI_CODEX_PROVIDER.token_filename).save(token)
            self._finished = True
            return token


def start_openai_codex_device_login(
    *,
    proxy: str | None = None,
    timeout_s: float = 600,
) -> CodexDeviceLogin:
    """Ask OpenAI for a one-time code the person can type on any phone."""
    payload = _post_json(
        _USER_CODE_URL,
        {"client_id": OPENAI_CODEX_PROVIDER.client_id},
        proxy,
    )
    if payload is None:
        raise CodexDeviceUnavailableError("OpenAI Codex device sign-in is unavailable.")
    device_auth_id = payload.get("device_auth_id")
    user_code = payload.get("user_code") or payload.get("usercode")
    if not isinstance(device_auth_id, str) or not isinstance(user_code, str):
        raise CodexDeviceError("OpenAI Codex did not return a sign-in code.")
    if not device_auth_id.strip() or not user_code.strip():
        raise CodexDeviceError("OpenAI Codex did not return a sign-in code.")
    return CodexDeviceLogin(
        device_auth_id=device_auth_id.strip(),
        user_code=user_code.strip(),
        proxy=proxy,
        timeout_s=timeout_s,
    )


def _poll_once(device_auth_id: str, user_code: str, proxy: str | None) -> dict[str, Any] | None:
    try:
        with _client(proxy) as client:
            response = client.post(
                _TOKEN_POLL_URL,
                json={"device_auth_id": device_auth_id, "user_code": user_code},
                headers={"Content-Type": "application/json"},
            )
    except httpx.HTTPError as exc:
        raise CodexDeviceError("OpenAI Codex sign-in could not be checked.") from exc
    if response.status_code in _PENDING:
        return None
    if response.status_code != 200:
        raise CodexDeviceError(f"OpenAI Codex sign-in failed with HTTP {response.status_code}.")
    body = _json_object(response)
    if body is None:
        raise CodexDeviceError("OpenAI Codex returned an unreadable sign-in result.")
    return body


def _exchange(issued: dict[str, Any], proxy: str | None) -> OAuthToken:
    code = issued.get("authorization_code")
    verifier = issued.get("code_verifier")
    if not isinstance(code, str) or not isinstance(verifier, str) or not code or not verifier:
        raise CodexDeviceError("OpenAI Codex sign-in did not return an authorization code.")
    data = {
        "grant_type": "authorization_code",
        "client_id": OPENAI_CODEX_PROVIDER.client_id,
        "code": code,
        "code_verifier": verifier,
        "redirect_uri": _DEVICE_REDIRECT,
    }
    try:
        with _client(proxy) as client:
            response = client.post(
                OPENAI_CODEX_PROVIDER.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
    except httpx.HTTPError as exc:
        raise CodexDeviceError("OpenAI Codex token exchange failed.") from exc
    if response.status_code != 200:
        raise CodexDeviceError(
            f"OpenAI Codex token exchange failed with HTTP {response.status_code}."
        )
    payload = _json_object(response)
    if payload is None:
        raise CodexDeviceError("OpenAI Codex token exchange returned an unreadable result.")
    access, refresh, expires_in = _token_fields(payload)
    account_id = _account_id(access)
    return OAuthToken(
        access=access,
        refresh=refresh,
        expires=int(time.time() * 1000 + expires_in * 1000),
        account_id=account_id,
    )


def _post_json(url: str, body: dict[str, str], proxy: str | None) -> dict[str, Any] | None:
    try:
        with _client(proxy) as client:
            response = client.post(
                url,
                json=body,
                headers={"Content-Type": "application/json"},
            )
    except httpx.HTTPError as exc:
        raise CodexDeviceError("OpenAI Codex sign-in could not be started.") from exc
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise CodexDeviceError(f"OpenAI Codex sign-in failed with HTTP {response.status_code}.")
    return _json_object(response)


def _json_object(response: httpx.Response) -> dict[str, Any] | None:
    try:
        payload = response.json()
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    return cast(dict[str, Any], payload)


def _token_fields(payload: dict[str, Any]) -> tuple[str, str, int]:
    access = payload.get("access_token")
    refresh = payload.get("refresh_token")
    expires_in = payload.get("expires_in")
    if not isinstance(access, str) or not isinstance(refresh, str) or not isinstance(expires_in, int):
        raise CodexDeviceError("OpenAI Codex token exchange returned an incomplete result.")
    if not access or not refresh or expires_in <= 0:
        raise CodexDeviceError("OpenAI Codex token exchange returned an incomplete result.")
    return access, refresh, expires_in


def _account_id(access_token: str) -> str | None:
    parts = access_token.split(".")
    if len(parts) != 3:
        return None
    try:
        padded = parts[1] + "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
    except (ValueError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    decoded = cast(dict[str, Any], payload)
    claim = OPENAI_CODEX_PROVIDER.jwt_claim_path
    name = OPENAI_CODEX_PROVIDER.account_id_claim
    if not isinstance(claim, str) or not isinstance(name, str):
        return None
    auth = decoded.get(claim)
    if not isinstance(auth, dict):
        return None
    account = cast(dict[str, Any], auth).get(name)
    return account if isinstance(account, str) and account else None


def _client(proxy: str | None) -> httpx.Client:
    if proxy:
        return httpx.Client(timeout=30.0, proxy=proxy, trust_env=False)
    return httpx.Client(timeout=30.0)
