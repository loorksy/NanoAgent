"""Browser connect flow for the official Claude Code CLI OAuth client.

Anthropic documents ``claude setup-token`` as the way to mint
``CLAUDE_CODE_OAUTH_TOKEN``. That command runs the Claude Code CLI's
public OAuth client (no client secret; PKCE) and, when a localhost
callback cannot be reached, uses ``code=true`` so the official
``platform.claude.com`` page shows ``code#state`` for the user to copy.

This module starts that same public-client authorization URL and
exchanges the returned code. It does not invent an Anthropic app secret
and does not collect Claude email/password. A custom redirect on the
NanoAgent origin is not registered on Anthropic's client, so a silent
HTTPS bounce back to this site is not possible.

The access token is persisted with ``apply_claude_code_oauth_token``
(``$HOME/.env`` / ``NANOAGENT_ENV_FILE``, mode 0600). Never log the
token, PKCE verifier, or authorization code.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit

import httpx

from nanobot.webui.claude_code_oauth import apply_claude_code_oauth_token
from nanobot.webui.settings_contracts import WebUISettingsError

# Public Claude Code CLI OAuth client. This is a public client_id (no
# secret) embedded in the official `claude` binary and used by
# `claude setup-token` / `/login`.
CLAUDE_CODE_OAUTH_CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
DEFAULT_AUTHORIZE_URL = "https://claude.com/cai/oauth/authorize"
DEFAULT_TOKEN_URL = "https://platform.claude.com/v1/oauth/token"
DEFAULT_REDIRECT_URI = "https://platform.claude.com/oauth/code/callback"
# setup-token requests inference-only; that is the long-lived CI token.
DEFAULT_SCOPE = "user:inference"
FLOW_TTL_S = 600
_TOKEN_EXCHANGE_TIMEOUT_S = 30.0
PROVIDER_NAME = "claude_code_cli"


@dataclass
class ClaudeCodeOAuthConnectFlow:
    """In-memory PKCE state for one Connect attempt."""

    flow_id: str
    state: str
    code_verifier: str
    authorization_url: str
    expires_at: float
    consumed: bool = False

    @property
    def expired(self) -> bool:
        return self.consumed or time.monotonic() >= self.expires_at

    @property
    def remaining_seconds(self) -> int:
        if self.consumed:
            return 0
        return max(0, int(self.expires_at - time.monotonic()))

    def cancel(self) -> None:
        self.consumed = True


def authorize_url_base() -> str:
    return (
        os.environ.get("NANOAGENT_CLAUDE_OAUTH_AUTHORIZE_URL", "").strip()
        or DEFAULT_AUTHORIZE_URL
    )


def token_url() -> str:
    return (
        os.environ.get("NANOAGENT_CLAUDE_OAUTH_TOKEN_URL", "").strip()
        or DEFAULT_TOKEN_URL
    )


def redirect_uri() -> str:
    return (
        os.environ.get("NANOAGENT_CLAUDE_OAUTH_REDIRECT_URI", "").strip()
        or DEFAULT_REDIRECT_URI
    )


def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def create_connect_flow(*, timeout_s: float = FLOW_TTL_S) -> ClaudeCodeOAuthConnectFlow:
    """Create PKCE state and the official Claude authorize URL."""
    flow_id = secrets.token_urlsafe(24)
    state = secrets.token_urlsafe(32)
    verifier, challenge = _pkce_pair()
    params = urlencode(
        {
            "code": "true",
            "response_type": "code",
            "client_id": CLAUDE_CODE_OAUTH_CLIENT_ID,
            "redirect_uri": redirect_uri(),
            "scope": DEFAULT_SCOPE,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    )
    return ClaudeCodeOAuthConnectFlow(
        flow_id=flow_id,
        state=state,
        code_verifier=verifier,
        authorization_url=f"{authorize_url_base()}?{params}",
        expires_at=time.monotonic() + max(30.0, float(timeout_s)),
    )


def parse_authorization_response(
    raw: str | None,
    *,
    explicit_code: str | None = None,
    explicit_state: str | None = None,
) -> tuple[str, str]:
    """Accept ``code#state``, a callback URL, or separate code/state fields."""
    code = (explicit_code or "").strip()
    state = (explicit_state or "").strip()
    text = (raw or "").strip()
    if text:
        if "#" in text and "://" not in text.split("#", 1)[0]:
            left, _, right = text.partition("#")
            code = code or left.strip()
            state = state or right.strip()
        elif "://" in text or text.startswith("/"):
            parsed = urlsplit(text)
            query = parse_qs(parsed.query)
            fragment = parse_qs(parsed.fragment)
            code = code or _first_query(query, "code") or _first_query(fragment, "code")
            state = state or _first_query(query, "state") or _first_query(fragment, "state")
            if not code and parsed.fragment and "#" not in parsed.fragment:
                # Official page uses ``code#state`` in the fragment.
                left, _, right = parsed.fragment.partition("#")
                if left and right:
                    code = left.strip()
                    state = state or right.strip()
        elif not code:
            code = text

    if not code:
        raise WebUISettingsError("Claude authorization code is required")
    if not state:
        raise WebUISettingsError("Claude sign-in state is required")
    return code, state


def _first_query(values: dict[str, list[str]], key: str) -> str:
    items = values.get(key) or []
    return items[0].strip() if items else ""


def _safe_exchange_error(status: int | None = None) -> WebUISettingsError:
    if status is not None:
        return WebUISettingsError(
            f"Claude token exchange failed ({status}).",
            status=502,
        )
    return WebUISettingsError("Claude token exchange failed.", status=502)


def exchange_authorization_code(
    *,
    code: str,
    state: str,
    code_verifier: str,
    post_fn: Any | None = None,
) -> str:
    """Exchange an authorization code at Anthropic's token endpoint.

    ``post_fn`` is a test seam. The production path uses httpx and never
    logs the request or response body.
    """
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri(),
        "client_id": CLAUDE_CODE_OAUTH_CLIENT_ID,
        "code_verifier": code_verifier,
        "state": state,
    }
    poster = post_fn or _httpx_post_json
    try:
        response = poster(token_url(), payload)
    except WebUISettingsError:
        raise
    except Exception as exc:
        raise _safe_exchange_error() from exc

    status = getattr(response, "status_code", None)
    if status not in {200, None}:
        raise _safe_exchange_error(int(status) if isinstance(status, int) else None)

    try:
        body = response.json() if hasattr(response, "json") else response
    except Exception as exc:
        raise _safe_exchange_error(status if isinstance(status, int) else None) from exc

    if not isinstance(body, dict):
        raise WebUISettingsError("Claude token exchange returned no access token.", status=502)
    token = body.get("access_token")
    if not isinstance(token, str) or not token.strip():
        raise WebUISettingsError("Claude token exchange returned no access token.", status=502)
    return token.strip()


def _httpx_post_json(url: str, payload: dict[str, str]) -> httpx.Response:
    return httpx.post(
        url,
        json=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        timeout=_TOKEN_EXCHANGE_TIMEOUT_S,
    )


def start_connect_payload(oauth_flows: Any, *, timeout_s: float = FLOW_TTL_S) -> dict[str, Any]:
    flow = create_connect_flow(timeout_s=timeout_s)
    oauth_flows.register(PROVIDER_NAME, flow.flow_id, flow)
    return {
        "status": "authorization_required",
        "provider": PROVIDER_NAME,
        "flow_id": flow.flow_id,
        "authorization_url": flow.authorization_url,
        "expires_in": flow.remaining_seconds,
        "completion_input": "authorization_code",
    }


def _lookup_flow(oauth_flows: Any, flow_id: str | None, state: str) -> ClaudeCodeOAuthConnectFlow:
    if flow_id:
        flow = oauth_flows.get(PROVIDER_NAME, flow_id)
        if flow is None:
            raise WebUISettingsError("Claude sign-in expired. Start again.", status=410)
        if not hmac.compare_digest(state, flow.state):
            raise WebUISettingsError("Invalid or expired Claude sign-in state.")
        return flow

    getter = getattr(oauth_flows, "get_by_state", None)
    if callable(getter):
        flow = getter(PROVIDER_NAME, state)
        if flow is not None:
            return flow
    raise WebUISettingsError("Invalid or expired Claude sign-in state.")


def complete_connect(
    *,
    oauth_flows: Any,
    flow_id: str | None,
    authorization_response: str | None = None,
    code: str | None = None,
    state: str | None = None,
    post_fn: Any | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    parsed_code, parsed_state = parse_authorization_response(
        authorization_response,
        explicit_code=code,
        explicit_state=state,
    )
    flow = _lookup_flow(oauth_flows, flow_id, parsed_state)
    token = exchange_authorization_code(
        code=parsed_code,
        state=parsed_state,
        code_verifier=flow.code_verifier,
        post_fn=post_fn,
    )
    oauth_flows.remove(PROVIDER_NAME, flow.flow_id, flow, cancel=False)
    flow.consumed = True
    if persist:
        return apply_claude_code_oauth_token(token)
    return {"access_token": token}
