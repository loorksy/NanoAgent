"""Room-scoped handoff. Depth is counted from the current session-message hop."""

from __future__ import annotations

from mokli.session.manager import SessionManager
from mokli.trading.desk.roster import DeskRole, role_for_session_key, role_for_token
from mokli.trading.desk.sessions import ensure_desk_session

MAX_HANDOFF_DEPTH = 3
DESK_HANDOFF_DEPTH_KEY = "desk_handoff_depth"


class DeskHandoffError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def can_handoff(source: DeskRole, target: DeskRole) -> bool:
    """Members share a room. A room lead may also pass a brief to the clerk."""
    if source.role_id == target.role_id:
        return False
    if source.room_id == target.room_id:
        return True
    return source.kind == "lead" and target.role_id == "clerk"


def authorize_desk_handoff(
    source_session_key: str,
    target_token: str,
    depth: int,
) -> DeskRole:
    if depth >= MAX_HANDOFF_DEPTH:
        raise DeskHandoffError("handoff depth exceeded")
    source = role_for_session_key(source_session_key)
    if source is None:
        raise DeskHandoffError("source is not a desk session")
    target = role_for_token(target_token)
    if target is None:
        raise DeskHandoffError("target is not a desk role")
    if not can_handoff(source, target):
        raise DeskHandoffError("target is outside the room")
    return target


def deliver_handoff(
    sessions: SessionManager,
    source_session_key: str,
    target_token: str,
    content: str,
    depth: int = 0,
) -> DeskRole:
    """Append the brief to the target thread. Does not place or confirm an order."""
    target = authorize_desk_handoff(source_session_key, target_token, depth)
    source = role_for_session_key(source_session_key)
    session = ensure_desk_session(sessions, target.role_id)
    session.add_message(
        "user",
        content,
        source_role=source.role_id if source else "",
        **{DESK_HANDOFF_DEPTH_KEY: depth + 1},
    )
    sessions.save(session)
    return target


def depth_from_metadata(metadata: object) -> int:
    if not isinstance(metadata, dict):
        return 0
    raw = metadata.get(DESK_HANDOFF_DEPTH_KEY, 0)
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
        return 0
    return raw
