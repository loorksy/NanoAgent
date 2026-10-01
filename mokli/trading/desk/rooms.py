"""Rooms built from the current team presets plus the execution desk."""

from __future__ import annotations

from dataclasses import dataclass

from mokli.trading.desk.roster import DeskRole, role_by_id, roster

_ROOM_ORDER = ("analysis", "news", "mtf", "debate", "execution", "journal")


@dataclass(frozen=True)
class DeskRoom:
    room_id: str
    lead_id: str
    member_ids: frozenset[str]


def _build_rooms() -> dict[str, DeskRoom]:
    members: dict[str, set[str]] = {room_id: set() for room_id in _ROOM_ORDER}
    leads: dict[str, str] = {}
    for role in roster():
        members.setdefault(role.room_id, set()).add(role.role_id)
        if role.kind == "lead":
            leads[role.room_id] = role.role_id
    rooms: dict[str, DeskRoom] = {}
    for room_id, ids in members.items():
        lead_id = leads.get(room_id, "")
        rooms[room_id] = DeskRoom(room_id, lead_id, frozenset(ids))
    return rooms


ROOMS = _build_rooms()


def room_by_id(room_id: str) -> DeskRoom | None:
    return ROOMS.get(room_id)


def room_of_agent(agent_id: str) -> str | None:
    role = role_by_id(agent_id)
    if role is None:
        return None
    return role.room_id


def members(room_id: str) -> tuple[DeskRole, ...]:
    room = ROOMS.get(room_id)
    if room is None:
        return ()
    found = [role_by_id(role_id) for role_id in sorted(room.member_ids)]
    return tuple(role for role in found if role is not None)


def same_room(source: DeskRole, target: DeskRole) -> bool:
    return source.room_id == target.room_id
