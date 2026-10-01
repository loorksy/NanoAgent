"""Idle research stays read-only and opt-in."""

from __future__ import annotations

from pathlib import Path

import pytest

from mokli.config.schema import TradingCronConfig
from mokli.session.manager import SessionManager
from mokli.trading.cron import GOLD_NEWS_JOB_ID, register_trading_cron_jobs
from mokli.trading.desk.idle import run_idle_shift
from mokli.trading.desk.roster import desk_session_key
from mokli.trading.policy_guard import PolicyViolation, validate_tool_call
from mokli.trading.turn_session import TurnSession, turn_session_scope


class _FakeCron:
    def __init__(self) -> None:
        self.jobs: dict[str, object] = {}

    def register_system_job(self, job: object) -> object:
        self.jobs[getattr(job, "id")] = job
        return job

    def remove_system_job(self, job_id: str) -> bool:
        return self.jobs.pop(job_id, None) is not None


def test_idle_research_defaults_off_and_disabled_cron_schedules_nothing() -> None:
    assert TradingCronConfig().enabled is False
    assert TradingCronConfig().idle_research is False
    cron = _FakeCron()
    register_trading_cron_jobs(cron, enabled=False)
    assert cron.jobs == {}


@pytest.mark.asyncio
async def test_idle_shift_notes_the_news_room_without_mt5(tmp_path) -> None:
    sessions = SessionManager(tmp_path)

    async def _note(_job: str) -> str:
        return "Gold news watch: medium — cpi"

    result = await run_idle_shift(
        GOLD_NEWS_JOB_ID,
        enabled=True,
        idle_research=True,
        sessions=sessions,
        note_for=_note,
    )
    assert result.status == "noted"
    lead = sessions.get_or_create(desk_session_key("lead_news"))
    assert any("cpi" in message["content"] for message in lead.messages)


@pytest.mark.asyncio
async def test_idle_shift_skips_when_a_goal_is_active(tmp_path) -> None:
    sessions = SessionManager(tmp_path)
    lead = sessions.get_or_create(desk_session_key("lead_news"))
    lead.add_message("assistant", "earlier")
    lead.metadata["goal_state"] = {"status": "active"}
    sessions.save(lead)
    before = len(lead.messages)

    async def _note(_job: str) -> str:
        return "should not be written"

    result = await run_idle_shift(
        GOLD_NEWS_JOB_ID,
        enabled=True,
        idle_research=True,
        sessions=sessions,
        note_for=_note,
    )
    assert result.status == "skipped"
    assert len(sessions.get_or_create(desk_session_key("lead_news")).messages) == before


@pytest.mark.asyncio
async def test_disabled_flags_do_not_write(tmp_path) -> None:
    sessions = SessionManager(tmp_path)

    async def _note(_job: str) -> str:
        return "nope"

    result = await run_idle_shift(
        GOLD_NEWS_JOB_ID,
        enabled=False,
        idle_research=True,
        sessions=sessions,
        note_for=_note,
    )
    assert result.status == "disabled"
    assert sessions.get_cached(desk_session_key("lead_news")) is None


def test_idle_turn_rejects_python_and_messages() -> None:
    with turn_session_scope(TurnSession(session_key="desk:lab_desk", idle_research=True)):
        with pytest.raises(PolicyViolation, match="Idle research"):
            validate_tool_call("run_python", {"code": "print(1)"})
        with pytest.raises(PolicyViolation, match="Idle research"):
            validate_tool_call("message", {"content": "hello"})


def test_idle_module_does_not_import_mt5_or_the_sandbox() -> None:
    text = Path("mokli/trading/desk/idle.py").read_text(encoding="utf-8")
    imports = [
        line
        for line in text.splitlines()
        if line.startswith("import ") or line.startswith("from ")
    ]
    blob = "\n".join(imports).lower()
    assert "mt5" not in blob
    assert "python_sandbox" not in blob
