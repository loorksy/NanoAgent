"""Persist ``CLAUDE_CODE_OAUTH_TOKEN`` for the official Claude Code CLI.

The systemd ``nanoagent-gateway`` unit sets ``HOME=/opt/nanoagent`` and
``EnvironmentFile=-/opt/nanoagent/.env``. The official ``claude`` binary
reads this variable from the process environment (not nanobot config JSON
and not ``ANTHROPIC_API_KEY``). Saving here:

1. Upserts the key in ``$HOME/.env`` (mode 0600) so a later restart still
   has it.
2. Updates ``os.environ`` so the next ``claude`` subprocess inherits the
   token without restarting the gateway or rotating the WebUI bootstrap
   token.

Do not log the token value. Do not start ``claude login``.
"""

from __future__ import annotations

import os
import stat
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Any

from loguru import logger

from nanobot.webui.settings_contracts import WebUISettingsError

ENV_KEY = "CLAUDE_CODE_OAUTH_TOKEN"
ENV_FILE_OVERRIDE = "NANOAGENT_ENV_FILE"


def resolve_env_file_path() -> Path:
    """Return the dotenv path used by the nanoagent service.

    Prefer ``NANOAGENT_ENV_FILE`` (tests / explicit override). Otherwise
    ``$HOME/.env``, which is ``/opt/nanoagent/.env`` under systemd.
    """
    override = os.environ.get(ENV_FILE_OVERRIDE, "").strip()
    if override:
        return Path(override).expanduser()
    home = os.environ.get("HOME", "").strip()
    if home:
        return Path(home) / ".env"
    return Path(".env")


def mask_token_last4(secret: str | None) -> str | None:
    """Return a last-4 hint only. Never return the stored token."""
    if not secret:
        return None
    if len(secret) <= 4:
        return "••••"
    return f"••••{secret[-4:]}"


def public_status() -> dict[str, Any]:
    current = os.environ.get(ENV_KEY, "").strip()
    return {
        "configured": bool(current),
        "hint": mask_token_last4(current),
        "env_key": ENV_KEY,
    }


def claude_code_oauth_configured() -> bool:
    return bool(os.environ.get(ENV_KEY, "").strip())


def _quote_env_value(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _is_env_key_line(line: str, key: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith(f"{key}=") or stripped.startswith(f"export {key}=")


def upsert_dotenv_key(path: Path, key: str, value: str | None) -> None:
    """Create or update a single dotenv key. Other lines are left unchanged."""
    existing_lines: list[str] = []
    if path.is_file():
        existing_lines = path.read_text(encoding="utf-8").splitlines()

    kept: list[str] = []
    replaced = False
    for line in existing_lines:
        if _is_env_key_line(line, key):
            if value is None:
                continue
            kept.append(f"{key}={_quote_env_value(value)}")
            replaced = True
        else:
            kept.append(line)

    if value is not None and not replaced:
        kept.append(f"{key}={_quote_env_value(value)}")

    text = "\n".join(kept)
    if text:
        text += "\n"

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".env.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_name, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(tmp_name, path)
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        with suppress(OSError):
            os.unlink(tmp_name)
        raise


def apply_claude_code_oauth_token(
    token: str | None,
    *,
    env_file: Path | None = None,
) -> dict[str, Any]:
    """Update in-process env and persist to the service dotenv file."""
    path = env_file or resolve_env_file_path()
    if token is None:
        os.environ.pop(ENV_KEY, None)
        upsert_dotenv_key(path, ENV_KEY, None)
        logger.info("Cleared Claude Code CLI OAuth token from process env and dotenv")
        return public_status()

    cleaned = token.strip()
    if not cleaned:
        raise WebUISettingsError("Claude Code CLI token is required")

    os.environ[ENV_KEY] = cleaned
    upsert_dotenv_key(path, ENV_KEY, cleaned)
    logger.info("Updated Claude Code CLI OAuth token in process env and dotenv")
    return public_status()
