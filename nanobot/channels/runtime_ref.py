"""Process-wide handle to the gateway ChannelManager.

The Agent API and the WebUI settings surface run in the same process. Channel
connect actions use this handle for hot reload instead of restarting the gateway.
"""

from __future__ import annotations

from typing import Any

_manager: Any | None = None


def bind_channel_manager(manager: Any | None) -> None:
    global _manager
    _manager = manager


def channel_manager() -> Any | None:
    return _manager
