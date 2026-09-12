"""No-op exec session manager — gold agent does not expose shell session tools."""

from __future__ import annotations


class ExecSessionManager:
    """Stub manager kept for agent loop lifecycle hooks."""

    async def terminate_by_owner(self, _owner_session_key: str) -> int:
        return 0

    async def close_all(self) -> None:
        return None
