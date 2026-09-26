"""Fernet-encrypted key/value store for local credentials (T-7.2).

Secrets live in ``<data dir>/secrets.enc`` (``~/.mokli/secrets.enc`` for the
default config). The master key comes from ``MOKLI_SECRET_KEY`` or is generated
once into ``<data dir>/secret.key`` with owner-only permissions. Writes are
atomic (temp file + fsync + ``os.replace`` + directory fsync) like the session
history writer in ``mokli/agent/memory.py``.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import stat
import threading
from contextlib import suppress
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

SECRET_KEY_ENV = "MOKLI_SECRET_KEY"
SECRETS_FILENAME = "secrets.enc"
KEY_FILENAME = "secret.key"

_OWNER_RW = stat.S_IRUSR | stat.S_IWUSR


class SecretStoreError(Exception):
    """Raised when the encrypted store cannot be read or decrypted."""


def default_secrets_dir() -> Path:
    """Instance data directory (``~/.mokli`` unless a custom config path is active)."""
    try:
        from mokli.config.paths import get_data_dir

        return get_data_dir()
    except Exception:
        return Path.home() / ".mokli"


def _fernet_key_from_text(raw: str) -> bytes:
    """Accept a genuine Fernet key or derive one deterministically from any passphrase."""
    text = raw.strip()
    candidate = text.encode("utf-8")
    try:
        Fernet(candidate)
        return candidate
    except (ValueError, TypeError):
        digest = hashlib.sha256(candidate).digest()
        return base64.urlsafe_b64encode(digest)


def _restrict_permissions(path: Path) -> None:
    with suppress(OSError, NotImplementedError):
        os.chmod(path, _OWNER_RW)


def atomic_write_bytes(path: Path, payload: bytes, *, mode: int = _OWNER_RW) -> None:
    """Durable owner-only write: temp file + fsync + replace + directory fsync."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        fd = os.open(str(tmp_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
        _restrict_permissions(path)
        with suppress(PermissionError, OSError):
            dir_fd = os.open(str(path.parent), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


class SecretStore:
    """Encrypted name → value store. Every operation re-reads the file (no plaintext cache)."""

    def __init__(
        self,
        path: Path | None = None,
        *,
        key_path: Path | None = None,
        master_key: bytes | str | None = None,
    ) -> None:
        self._path = path if path is not None else default_secrets_dir() / SECRETS_FILENAME
        self._key_path = key_path if key_path is not None else self._path.parent / KEY_FILENAME
        self._explicit_key = (
            _fernet_key_from_text(master_key) if isinstance(master_key, str) else master_key
        )
        self._fernet: Fernet | None = None
        self._lock = threading.RLock()

    @property
    def path(self) -> Path:
        return self._path

    @property
    def key_path(self) -> Path:
        return self._key_path

    # -- key management -----------------------------------------------------

    def _load_key(self) -> bytes:
        if self._explicit_key is not None:
            return self._explicit_key
        env_value = os.environ.get(SECRET_KEY_ENV)
        if env_value and env_value.strip():
            return _fernet_key_from_text(env_value)
        if self._key_path.exists():
            raw = self._key_path.read_bytes().strip()
            if raw:
                try:
                    Fernet(raw)
                except (ValueError, TypeError) as exc:
                    raise SecretStoreError(f"invalid master key file: {self._key_path}") from exc
                return raw
        key = Fernet.generate_key()
        atomic_write_bytes(self._key_path, key + b"\n")
        return key

    def _cipher(self) -> Fernet:
        if self._fernet is None:
            self._fernet = Fernet(self._load_key())
        return self._fernet

    # -- payload ------------------------------------------------------------

    def _read_all(self) -> dict[str, str]:
        if not self._path.exists():
            return {}
        token = self._path.read_bytes().strip()
        if not token:
            return {}
        try:
            plain = self._cipher().decrypt(token)
        except InvalidToken as exc:
            raise SecretStoreError(f"cannot decrypt secret store: {self._path}") from exc
        try:
            data: object = json.loads(plain.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SecretStoreError(f"corrupt secret store payload: {self._path}") from exc
        if not isinstance(data, dict):
            raise SecretStoreError(f"corrupt secret store payload: {self._path}")
        out: dict[str, str] = {}
        for key, value in data.items():  # pyright: ignore[reportUnknownVariableType]
            if isinstance(key, str) and isinstance(value, str):
                out[key] = value
        return out

    def _write_all(self, data: dict[str, str]) -> None:
        plain = json.dumps(data, ensure_ascii=False, sort_keys=True).encode("utf-8")
        atomic_write_bytes(self._path, self._cipher().encrypt(plain))

    # -- public API ---------------------------------------------------------

    def get(self, name: str) -> str | None:
        with self._lock:
            return self._read_all().get(name)

    def set(self, name: str, value: str) -> None:
        if not name:
            raise ValueError("secret name must be non-empty")
        with self._lock:
            data = self._read_all()
            data[name] = value
            self._write_all(data)

    def delete(self, name: str) -> bool:
        with self._lock:
            data = self._read_all()
            if name not in data:
                return False
            del data[name]
            self._write_all(data)
            return True

    def names(self) -> list[str]:
        with self._lock:
            return sorted(self._read_all())


_store: SecretStore | None = None
_store_lock = threading.Lock()


def get_secret_store() -> SecretStore:
    """Process-wide store bound to the default secrets directory."""
    global _store
    with _store_lock:
        if _store is None:
            _store = SecretStore()
        return _store


def set_secret_store_for_tests(store: SecretStore | None) -> None:
    global _store
    with _store_lock:
        _store = store


def resolve_secret(config_value: str | None, name: str, *, store: SecretStore | None = None) -> str:
    """Prefer a non-empty config value; otherwise fall back to the encrypted store."""
    if config_value and config_value.strip():
        return config_value.strip()
    target = store if store is not None else get_secret_store()
    try:
        stored = target.get(name)
    except (SecretStoreError, OSError):
        return ""
    return (stored or "").strip()
