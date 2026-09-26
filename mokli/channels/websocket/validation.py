"""WebSocket setup validation owned by the channel package."""

from typing import Any

from mokli.channels.contracts import ChannelValidationContext
from mokli.channels.validation import check, enabled, official_action, payload


def validate(values: dict[str, Any], _context: ChannelValidationContext) -> dict[str, Any]:
    checks = [
        check(
            "managed",
            "Managed by Mokli",
            "pass",
            "The browser workbench prepares the local WebSocket channel.",
            action_url=official_action("websocket"),
        )
    ]
    status = "connected" if enabled(values) else "configured"
    return payload("websocket", status, checks, can_enable=True)


__all__ = ["validate"]
