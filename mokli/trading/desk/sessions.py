"""Create and restore persistent desk sessions. Keys never come from model text."""

from __future__ import annotations

from mokli.session.manager import Session, SessionManager
from mokli.session.session_handles import SESSION_HANDLE_METADATA_KEY
from mokli.trading.desk.roster import (
    DeskRole,
    desk_session_key,
    lead_for_preset,
    require_role,
    standing_roles,
)


def ensure_desk_session(sessions: SessionManager, role_id: str) -> Session:
    role = require_role(role_id)
    session = sessions.get_or_create(desk_session_key(role.role_id))
    session.metadata["desk_role_id"] = role.role_id
    session.metadata["desk_room_id"] = role.room_id
    session.metadata[SESSION_HANDLE_METADATA_KEY] = role.handle
    sessions.save(session)
    return session


def seed_standing_sessions(sessions: SessionManager) -> list[str]:
    keys: list[str] = []
    for role in standing_roles():
        session = ensure_desk_session(sessions, role.role_id)
        keys.append(session.key)
    return keys


def append_session_note(
    sessions: SessionManager,
    role: DeskRole,
    content: str,
    **metadata: object,
) -> Session:
    session = ensure_desk_session(sessions, role.role_id)
    session.add_message("assistant", content, **metadata)
    sessions.save(session)
    return session


def persist_room_brief(
    sessions: SessionManager | None,
    preset_name: str,
    briefing: str,
) -> str | None:
    """Store a swarm brief on the room lead's thread. No model chooses the path."""
    if sessions is None or not briefing.strip():
        return None
    lead = lead_for_preset(preset_name)
    if lead is None:
        return None
    session = append_session_note(
        sessions,
        lead,
        briefing,
        desk_brief=True,
        preset=preset_name,
    )
    return session.key
