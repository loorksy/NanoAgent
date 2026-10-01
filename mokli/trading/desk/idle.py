"""Idle research writes a note into the news room and cannot act."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal

from mokli.session.goal_state import sustained_goal_active
from mokli.session.manager import SessionManager
from mokli.trading.desk.profiles import IDLE_TOOLS
from mokli.trading.desk.roster import require_role
from mokli.trading.desk.sessions import append_session_note
from mokli.trading.policy_guard import PolicyViolation
from mokli.trading.turn_session import current_turn_session

IdleStatus = Literal["disabled", "skipped", "noted"]
NEWS_LEAD_ID = "lead_news"


@dataclass(frozen=True)
class IdleShiftResult:
    status: IdleStatus
    note: str = ""
    session_key: str | None = None


def assert_idle_tool(tool_name: str) -> None:
    if tool_name not in IDLE_TOOLS:
        raise PolicyViolation(f"Idle research cannot call {tool_name}")


def desk_is_busy(sessions: SessionManager | None) -> bool:
    """True when an operator turn is open or any cached session has an active goal."""
    turn = current_turn_session()
    if turn is not None and not turn.idle_research:
        return True
    if sessions is None:
        return False
    for session in list(sessions._cache.values()):
        if sustained_goal_active(session.metadata):
            return True
    return False


async def run_idle_shift(
    job_name: str,
    *,
    enabled: bool,
    idle_research: bool,
    sessions: SessionManager | None = None,
    busy: bool | None = None,
    note_for: Callable[[str], Awaitable[str | None]] | None = None,
) -> IdleShiftResult:
    """Write one read-only note. Never pushes a channel and never calls MT5."""
    if not enabled or not idle_research:
        return IdleShiftResult("disabled")
    if busy if busy is not None else desk_is_busy(sessions):
        return IdleShiftResult("skipped")
    if sessions is None:
        return IdleShiftResult("skipped")
    producer = note_for or _default_note
    text = (await producer(job_name) or "").strip()
    if not text:
        text = "Idle research: nothing new"
    lead = require_role(NEWS_LEAD_ID)
    session = append_session_note(
        sessions,
        lead,
        text,
        desk_idle=True,
        idle_job=job_name,
    )
    return IdleShiftResult("noted", note=text, session_key=session.key)


async def _default_note(job_name: str) -> str | None:
    from mokli.trading.cron import (
        GOLD_NEWS_JOB_ID,
        GOLD_SCAN_JOB_ID,
        run_gold_news_job,
        run_gold_scan_job,
    )

    if job_name == GOLD_NEWS_JOB_ID:
        return await run_gold_news_job()
    if job_name == GOLD_SCAN_JOB_ID:
        return await run_gold_scan_job()
    return None
