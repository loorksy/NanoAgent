"""Bearer tokens with scopes for web / device / service clients (07 §8).

Tokens are random secrets stored hashed in SQLite (``gateway_clients`` +
``gateway_tokens``); the in-memory :mod:`nanobot.webui.gateway_tokens` store is
not suitable because device tokens must survive restarts and be revocable.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
from collections.abc import Awaitable, Callable
from typing import Literal, TypedDict, cast

from aiohttp import web

from nanobot.agent_api.db import Database, row_to_dict
from nanobot.agent_api.errors import ApiError
from nanobot.agent_api.events import now_ms

Scope = Literal["chat", "read", "approve", "control", "push", "admin"]
ClientKind = Literal["web", "device", "service"]
ALL_SCOPES: tuple[Scope, ...] = ("chat", "read", "approve", "control", "push", "admin")
DEFAULT_SCOPES: dict[ClientKind, tuple[Scope, ...]] = {
    "web": ("chat", "read", "approve", "control"),
    "device": ("chat", "read", "approve", "control", "push"),
    "service": ("read",),
}
TOKEN_PREFIX = "nbat_"
BOOTSTRAP_CLIENT_ID = "bootstrap"
PRINCIPAL_KEY = web.RequestKey["Principal"]("agent_api_principal")
PUBLIC_PATHS: frozenset[str] = frozenset({"/health", "/api/v2/health", "/api/v2/devices/pair"})


class Principal(TypedDict):
    client_id: str
    kind: ClientKind
    scopes: list[Scope]
    label: str
    locale: str


class ClientRecord(TypedDict):
    id: str
    kind: ClientKind
    scopes: list[Scope]
    label: str
    locale: str
    created_at: int
    revoked_at: int | None


class IssuedToken(TypedDict):
    token: str
    client: ClientRecord
    expires_at: int | None


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _kind(value: object) -> ClientKind:
    if value in ("web", "device", "service"):
        return value
    return "service"


def parse_scopes(value: object) -> list[Scope]:
    if isinstance(value, str):
        parts: list[object] = [part.strip() for part in value.split(",")]
    elif isinstance(value, list):
        parts = list(cast(list[object], value))
    else:
        return []
    return [part for part in parts if isinstance(part, str) and part in ALL_SCOPES]


def _client(row: sqlite3.Row) -> ClientRecord:
    record = row_to_dict(row)
    created = record.get("created_at")
    revoked = record.get("revoked_at")
    return {
        "id": str(record["id"]),
        "kind": _kind(record.get("kind")),
        "scopes": parse_scopes(record.get("scopes")),
        "label": str(record.get("label") or ""),
        "locale": str(record.get("locale") or "en"),
        "created_at": created if isinstance(created, int) else 0,
        "revoked_at": revoked if isinstance(revoked, int) else None,
    }


def principal_for(client: ClientRecord) -> Principal:
    return {
        "client_id": client["id"],
        "kind": client["kind"],
        "scopes": list(client["scopes"]),
        "label": client["label"],
        "locale": client["locale"],
    }


class TokenStore:
    def __init__(
        self,
        db: Database,
        *,
        bootstrap_token: str = "",
        default_ttl_seconds: int = 900,
    ) -> None:
        self._db = db
        self._bootstrap = bootstrap_token
        self.default_ttl_seconds = default_ttl_seconds

    @property
    def bootstrap_token(self) -> str:
        return self._bootstrap

    def ensure_bootstrap_token(self) -> str:
        if not self._bootstrap:
            self._bootstrap = f"{TOKEN_PREFIX}{secrets.token_urlsafe(32)}"
        return self._bootstrap

    # -- clients / tokens -----------------------------------------------------

    def create_client(
        self,
        kind: ClientKind,
        *,
        scopes: list[Scope] | None = None,
        label: str = "",
        locale: str = "en",
    ) -> ClientRecord:
        client_id = f"c_{secrets.token_hex(8)}"
        granted = list(scopes) if scopes is not None else list(DEFAULT_SCOPES[kind])
        granted = [scope for scope in granted if scope != "admin"]
        with self._db.cursor() as cur:
            cur.execute(
                "INSERT INTO gateway_clients(id, kind, scopes, label, locale, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (client_id, kind, ",".join(granted), label, locale, now_ms()),
            )
        client = self.get_client(client_id)
        assert client is not None
        return client

    def get_client(self, client_id: str) -> ClientRecord | None:
        with self._db.cursor() as cur:
            row = cur.execute(
                "SELECT * FROM gateway_clients WHERE id = ?", (client_id,),
            ).fetchone()
        return _client(row) if row is not None else None

    def list_clients(self, *, include_revoked: bool = False) -> list[ClientRecord]:
        where = "" if include_revoked else "WHERE revoked_at IS NULL "
        with self._db.cursor() as cur:
            rows = cur.execute(
                f"SELECT * FROM gateway_clients {where}ORDER BY created_at DESC",
            ).fetchall()
        return [_client(row) for row in rows]

    def issue(
        self,
        kind: ClientKind,
        *,
        scopes: list[Scope] | None = None,
        label: str = "",
        locale: str = "en",
        ttl_seconds: int | None = None,
        client_id: str | None = None,
    ) -> IssuedToken:
        client = self.get_client(client_id) if client_id else None
        if client is None:
            client = self.create_client(kind, scopes=scopes, label=label, locale=locale)
        ttl = self.default_ttl_seconds if ttl_seconds is None and kind == "web" else ttl_seconds
        expires_at = now_ms() + int(ttl) * 1000 if ttl is not None and ttl > 0 else None
        token = f"{TOKEN_PREFIX}{secrets.token_urlsafe(32)}"
        with self._db.cursor() as cur:
            cur.execute(
                "INSERT INTO gateway_tokens(token_hash, client_id, created_at, expires_at) "
                "VALUES (?, ?, ?, ?)",
                (_hash(token), client["id"], now_ms(), expires_at),
            )
        return {"token": token, "client": client, "expires_at": expires_at}

    def authenticate(self, token: str | None) -> Principal | None:
        if not token:
            return None
        if self._bootstrap and hmac.compare_digest(token, self._bootstrap):
            return {
                "client_id": BOOTSTRAP_CLIENT_ID,
                "kind": "service",
                "scopes": list(ALL_SCOPES),
                "label": "bootstrap",
                "locale": "en",
            }
        with self._db.cursor() as cur:
            row = cur.execute(
                "SELECT t.expires_at AS expires_at, c.* FROM gateway_tokens t "
                "JOIN gateway_clients c ON c.id = t.client_id WHERE t.token_hash = ?",
                (_hash(token),),
            ).fetchone()
        if row is None:
            return None
        record = row_to_dict(row)
        expires = record.get("expires_at")
        if isinstance(expires, int) and expires < now_ms():
            return None
        client = _client(row)
        if client["revoked_at"] is not None:
            return None
        return principal_for(client)

    def revoke_client(self, client_id: str) -> bool:
        with self._db.cursor() as cur:
            cur.execute(
                "UPDATE gateway_clients SET revoked_at = ? WHERE id = ? AND revoked_at IS NULL",
                (now_ms(), client_id),
            )
            changed = cur.rowcount > 0
            cur.execute("DELETE FROM gateway_tokens WHERE client_id = ?", (client_id,))
        return changed

    def purge_expired(self) -> int:
        with self._db.cursor() as cur:
            cur.execute(
                "DELETE FROM gateway_tokens WHERE expires_at IS NOT NULL AND expires_at < ?",
                (now_ms(),),
            )
            return max(cur.rowcount, 0)

    # -- pairing codes ------------------------------------------------------

    def create_pairing_code(self, *, label: str = "", ttl_seconds: int = 300) -> tuple[str, int]:
        code = f"{secrets.randbelow(10**8):08d}"
        expires_at = now_ms() + ttl_seconds * 1000
        with self._db.cursor() as cur:
            cur.execute(
                "INSERT INTO pairing_codes(code, label, created_at, expires_at) VALUES (?, ?, ?, ?)",
                (code, label, now_ms(), expires_at),
            )
        return code, expires_at

    def redeem_pairing_code(self, code: str, *, label: str = "", locale: str = "en") -> IssuedToken:
        with self._db.cursor() as cur:
            row = cur.execute(
                "SELECT * FROM pairing_codes WHERE code = ?", (code,),
            ).fetchone()
            if row is None:
                raise ApiError(404, "pairing_code_invalid")
            record = row_to_dict(row)
            expires = record.get("expires_at")
            if record.get("used_at") is not None:
                raise ApiError(409, "pairing_code_used")
            if isinstance(expires, int) and expires < now_ms():
                raise ApiError(410, "pairing_code_expired")
            cur.execute("UPDATE pairing_codes SET used_at = ? WHERE code = ?", (now_ms(), code))
            stored_label = str(record.get("label") or "")
        return self.issue("device", label=label or stored_label, locale=locale, ttl_seconds=None)


# ---------------------------------------------------------------------------
# request helpers
# ---------------------------------------------------------------------------


def bearer_from_request(request: web.Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        return token or None
    query_token = request.query.get("token")
    return query_token or None


def principal_of(request: web.Request) -> Principal:
    principal = request.get(PRINCIPAL_KEY)
    if principal is None:
        raise ApiError(401, "unauthorized")
    return principal


def require_scope(request: web.Request, scope: Scope) -> Principal:
    principal = principal_of(request)
    if scope not in principal["scopes"] and "admin" not in principal["scopes"]:
        raise ApiError(403, "forbidden", "auth.missing_scope", {"scope": scope})
    return principal


def is_admin(principal: Principal) -> bool:
    return "admin" in principal["scopes"]


Handler = Callable[[web.Request], Awaitable[web.StreamResponse]]


def auth_middleware_factory(store: TokenStore) -> Callable[..., Awaitable[web.StreamResponse]]:
    @web.middleware
    async def middleware(request: web.Request, handler: Handler) -> web.StreamResponse:
        if request.method == "OPTIONS" or request.path in PUBLIC_PATHS:
            return await handler(request)
        principal = store.authenticate(bearer_from_request(request))
        if principal is None:
            raise ApiError(401, "unauthorized")
        request[PRINCIPAL_KEY] = principal
        return await handler(request)

    return middleware
