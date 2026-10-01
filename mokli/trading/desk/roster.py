"""Stable desk identities. Role ids match preset agent ids where a preset exists."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from mokli.session.keys import session_key_for_channel

DESK_CHANNEL = "desk"
DeskKind = Literal["lead", "specialist", "clerk", "journal"]

_HANDLE_OVERRIDES = {
    "h1_analyst": "honeanalyst",
    "h4_analyst": "hfouranalyst",
    "d1_analyst": "doneanalyst",
}


@dataclass(frozen=True)
class DeskRole:
    role_id: str
    display_name: str
    room_id: str
    role_file: str
    kind: DeskKind
    profile: str

    @property
    def standing(self) -> bool:
        """Seeded as a persistent session. Specialists stay task-scoped."""
        return self.kind in {"lead", "clerk", "journal"}

    @property
    def session_key(self) -> str:
        return desk_session_key(self.role_id)

    @property
    def handle(self) -> str:
        return handle_for(self.role_id)


def desk_session_key(role_id: str) -> str:
    return session_key_for_channel(DESK_CHANNEL, role_id)


def is_desk_session(session_key: str | None) -> bool:
    return bool(session_key) and session_key.startswith(f"{DESK_CHANNEL}:")


def handle_for(role_id: str) -> str:
    override = _HANDLE_OVERRIDES.get(role_id)
    if override:
        return override
    letters = "".join(ch for ch in role_id.lower() if "a" <= ch <= "z")
    if len(letters) < 4:
        letters = f"{letters}desk"
    return letters[:16]


def _role(
    role_id: str,
    display_name: str,
    room_id: str,
    role_file: str,
    kind: DeskKind,
    profile: str,
) -> DeskRole:
    return DeskRole(role_id, display_name, room_id, role_file, kind, profile)


_ROLES: tuple[DeskRole, ...] = (
    _role("lead_analysis", "Analysis lead", "analysis", "lead", "lead", "lead"),
    _role("lead_news", "News lead", "news", "lead", "lead", "lead"),
    _role("lead_mtf", "MTF lead", "mtf", "lead", "lead", "lead"),
    _role("lead_debate", "Debate lead", "debate", "lead", "lead", "lead"),
    _role("lead_execution", "Execution lead", "execution", "lead", "lead", "lead"),
    _role("macro_analyst", "Macro Analyst", "analysis", "macro", "specialist", "analyst"),
    _role("structure_analyst", "Structure Analyst", "analysis", "structure", "specialist", "analyst"),
    _role("liquidity_analyst", "Liquidity Analyst", "analysis", "liquidity", "specialist", "analyst"),
    _role("risk_officer", "Risk Officer", "analysis", "risk", "specialist", "risk"),
    _role("lead_analyst", "Lead Analyst", "analysis", "lead", "specialist", "analyst"),
    _role("chart_desk", "Chart", "analysis", "lead", "specialist", "chart"),
    _role("lab_desk", "Lab", "analysis", "lead", "specialist", "lab"),
    _role("news_scanner", "News Scanner", "news", "news", "specialist", "analyst"),
    _role("event_analyst", "Event Analyst", "news", "event", "specialist", "analyst"),
    _role("scenario_planner", "Scenario Planner", "news", "scenario", "specialist", "analyst"),
    _role("h1_analyst", "H1 Analyst", "mtf", "timeframe", "specialist", "analyst"),
    _role("h4_analyst", "H4 Analyst", "mtf", "timeframe", "specialist", "analyst"),
    _role("d1_analyst", "D1 Analyst", "mtf", "timeframe", "specialist", "analyst"),
    _role("mtf_synthesizer", "MTF Synthesizer", "mtf", "mtf_synthesizer", "specialist", "analyst"),
    _role("bull_advocate", "Bull Advocate", "debate", "bull", "specialist", "analyst"),
    _role("bear_advocate", "Bear Advocate", "debate", "bear", "specialist", "analyst"),
    _role("risk_manager", "Risk Manager", "debate", "risk", "specialist", "risk"),
    _role("clerk", "Order clerk", "execution", "lead", "clerk", "clerk"),
    _role("journal", "Journal", "journal", "lead", "journal", "journal"),
)

_BY_ID = {role.role_id: role for role in _ROLES}
_BY_HANDLE = {role.handle: role for role in _ROLES}
if len(_BY_ID) != len(_ROLES) or len(_BY_HANDLE) != len(_ROLES):
    raise RuntimeError("desk role ids and handles must be unique")


def roster() -> tuple[DeskRole, ...]:
    return _ROLES


def role_by_id(role_id: str) -> DeskRole | None:
    return _BY_ID.get(role_id)


def require_role(role_id: str) -> DeskRole:
    role = role_by_id(role_id)
    if role is None:
        raise KeyError(role_id)
    return role


def role_for_session_key(session_key: str | None) -> DeskRole | None:
    if not is_desk_session(session_key):
        return None
    role_id = session_key.split(":", 1)[1] if session_key else ""
    return role_by_id(role_id)


def role_for_token(token: str) -> DeskRole | None:
    """Resolve a role id, session key, or public handle."""
    text = (token or "").strip()
    if not text:
        return None
    if text.startswith("@"):
        text = text[1:]
    by_id = role_by_id(text)
    if by_id is not None:
        return by_id
    by_session = role_for_session_key(text)
    if by_session is not None:
        return by_session
    return _BY_HANDLE.get(text.lower())


def standing_roles() -> tuple[DeskRole, ...]:
    return tuple(role for role in _ROLES if role.standing)


PRESET_ROOMS = {
    "gold_analysis_committee": "analysis",
    "gold_news_war_room": "news",
    "gold_mtf_panel": "mtf",
    "gold_debate_desk": "debate",
}


def lead_for_preset(preset_name: str) -> DeskRole | None:
    room_id = PRESET_ROOMS.get(preset_name)
    if room_id is None:
        return None
    return role_by_id(f"lead_{room_id}")
