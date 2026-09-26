"""Unified ``job`` view over cron jobs and sustained goals (07 §9)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal, Protocol, TypedDict, cast

from nanobot.agent_api.errors import ApiError
from nanobot.agent_api.events import JsonObject
from nanobot.cron.types import CronJob, CronSchedule
from nanobot.session.goal_state import goal_state_ws_blob

JobKind = Literal["cron", "goal"]
GOAL_PREFIX = "goal:"


class JobRecord(TypedDict):
    job_id: str
    kind: JobKind
    name: str
    status: str
    progress: JsonObject | None
    next_run_at: int | None
    last_run_at: int | None
    last_status: str | None
    session: str | None


class CronServiceLike(Protocol):
    def list_jobs(self, include_disabled: bool = ...) -> list[CronJob]: ...
    def get_job(self, job_id: str) -> CronJob | None: ...
    def enable_job(self, job_id: str, enabled: bool = ...) -> CronJob | None: ...
    def remove_job(self, job_id: str) -> Literal["removed", "protected", "not_found"]: ...
    def add_job(
        self,
        name: str,
        schedule: CronSchedule,
        message: str,
        deliver: bool = ...,
        channel: str | None = ...,
        to: str | None = ...,
        delete_after_run: bool = ...,
        channel_meta: dict[str, object] | None = ...,
        session_key: str | None = ...,
        origin_channel: str | None = ...,
        origin_chat_id: str | None = ...,
        origin_metadata: dict[str, object] | None = ...,
    ) -> CronJob: ...


class SessionManagerLike(Protocol):
    def list_sessions(self) -> list[dict[str, object]]: ...
    def read_session_metadata(self, key: str) -> dict[str, object] | None: ...


def cron_job_record(job: CronJob) -> JobRecord:
    return {
        "job_id": job.id,
        "kind": "cron",
        "name": job.name,
        "status": "scheduled" if job.enabled else "paused",
        "progress": None,
        "next_run_at": job.state.next_run_at_ms if job.enabled else None,
        "last_run_at": job.state.last_run_at_ms,
        "last_status": job.state.last_status,
        "session": job.payload.session_key,
    }


def goal_job_record(session_key: str, metadata: dict[str, object]) -> JobRecord | None:
    blob = goal_state_ws_blob(metadata)
    if not blob.get("active") and blob.get("status") != "blocked":
        return None
    progress: JsonObject = {}
    for key in ("ui_summary", "recap", "objective"):
        value = blob.get(key)
        if isinstance(value, str) and value:
            progress[key] = value
    status_value = blob.get("status")
    return {
        "job_id": f"{GOAL_PREFIX}{session_key}",
        "kind": "goal",
        "name": str(progress.get("ui_summary") or progress.get("objective") or "goal")[:80],
        "status": str(status_value) if isinstance(status_value, str) else "active",
        "progress": progress or None,
        "next_run_at": None,
        "last_run_at": None,
        "last_status": None,
        "session": session_key,
    }


class JobsService:
    def __init__(
        self,
        cron: CronServiceLike | None,
        sessions: SessionManagerLike | None,
        *,
        timezone: str | None = None,
    ) -> None:
        self._cron = cron
        self._sessions = sessions
        self._timezone = timezone

    def list(self) -> list[JobRecord]:
        records: list[JobRecord] = []
        if self._cron is not None:
            records.extend(cron_job_record(job) for job in self._cron.list_jobs(include_disabled=True))
        if self._sessions is not None:
            for info in self._sessions.list_sessions():
                key = info.get("key")
                if not isinstance(key, str):
                    continue
                metadata = self._sessions.read_session_metadata(key)
                if not metadata:
                    continue
                goal = goal_job_record(key, metadata)
                if goal is not None:
                    records.append(goal)
        return records

    def get(self, job_id: str) -> JobRecord | None:
        if job_id.startswith(GOAL_PREFIX):
            if self._sessions is None:
                return None
            key = job_id[len(GOAL_PREFIX):]
            metadata = self._sessions.read_session_metadata(key)
            return goal_job_record(key, metadata) if metadata else None
        if self._cron is None:
            return None
        job = self._cron.get_job(job_id)
        return cron_job_record(job) if job is not None else None

    def _require_cron(self, job_id: str) -> CronServiceLike:
        if job_id.startswith(GOAL_PREFIX):
            raise ApiError(501, "not_supported", "job.goal_control_not_supported")
        if self._cron is None:
            raise ApiError(501, "not_available", "not_available", {"feature": "cron"})
        return self._cron

    def pause(self, job_id: str) -> JobRecord:
        cron = self._require_cron(job_id)
        job = cron.enable_job(job_id, False)
        if job is None:
            raise ApiError(404, "job_not_found")
        return cron_job_record(job)

    def resume(self, job_id: str) -> JobRecord:
        cron = self._require_cron(job_id)
        job = cron.enable_job(job_id, True)
        if job is None:
            raise ApiError(404, "job_not_found")
        return cron_job_record(job)

    def cancel(self, job_id: str) -> Literal["removed", "protected"]:
        cron = self._require_cron(job_id)
        result = cron.remove_job(job_id)
        if result == "not_found":
            raise ApiError(404, "job_not_found")
        return result

    def create(self, body: JsonObject, *, session_key: str | None = None) -> JobRecord:
        if self._cron is None:
            raise ApiError(501, "not_available", "not_available", {"feature": "cron"})
        name = body.get("name")
        message = body.get("message")
        schedule_raw = body.get("schedule")
        if not isinstance(name, str) or not name.strip():
            raise ApiError(400, "invalid_field", details={"field": "name"})
        if not isinstance(message, str) or not message.strip():
            raise ApiError(400, "invalid_field", details={"field": "message"})
        if not isinstance(schedule_raw, dict):
            raise ApiError(400, "invalid_field", details={"field": "schedule"})
        schedule = _schedule_from_body(cast(JsonObject, schedule_raw), self._timezone)
        try:
            job = self._cron.add_job(
                name.strip(),
                schedule,
                message.strip(),
                session_key=session_key,
            )
        except ValueError as exc:
            raise ApiError(400, "invalid_schedule", details={"reason": str(exc)}) from exc
        return cron_job_record(job)


def _schedule_from_body(raw: JsonObject, timezone: str | None) -> CronSchedule:
    kind = raw.get("kind")
    if kind not in ("at", "every", "cron"):
        raise ApiError(400, "invalid_field", details={"field": "schedule.kind"})
    at_ms = raw.get("at_ms")
    every_ms = raw.get("every_ms")
    expr = raw.get("expr")
    tz = raw.get("tz")
    return CronSchedule(
        kind=kind,
        at_ms=at_ms if isinstance(at_ms, int) else None,
        every_ms=every_ms if isinstance(every_ms, int) else None,
        expr=expr if isinstance(expr, str) else None,
        tz=tz if isinstance(tz, str) else timezone,
    )


JobsFactory = Callable[[], JobsService]
