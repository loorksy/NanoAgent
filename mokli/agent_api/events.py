"""Public event contract (07 §4) and translators from internal runtime events.

No ``Any`` at this boundary: ``data`` is a JSON object whose shape depends on
``kind``; the per-kind builders below are the only producers.
"""

from __future__ import annotations

import time
from typing import Literal, TypedDict

from mokli.bus.runtime_events import (
    GoalStateChanged,
    SessionTurnStarted,
    TurnCompleted,
    TurnRunStatusChanged,
    TurnRuntimeAdmitted,
    UserInputAccepted,
)
from mokli.events import AgentEvent, DecisionCompletedEvent, RetryStatusEvent, TeamRoleEvent
from mokli.session.goal_state import goal_state_ws_blob

EventKind = Literal[
    "delta",
    "state",
    "tool",
    "subagent",
    "structured",
    "artifact",
    "approval",
    "notification",
    "job",
    "end",
    "diagnostic",
    "retry",
]
EVENT_KINDS: tuple[EventKind, ...] = (
    "delta",
    "state",
    "tool",
    "subagent",
    "structured",
    "artifact",
    "approval",
    "notification",
    "job",
    "end",
    "diagnostic",
    "retry",
)

SessionState = Literal["working", "waiting", "completed"]
Outcome = Literal["ok", "cancelled", "error", "expired"]
JsonObject = dict[str, object]


class GatewayEvent(TypedDict):
    id: str
    session: str
    run: str | None
    ts: int
    kind: EventKind
    data: JsonObject


class WaitingFor(TypedDict, total=False):
    kind: Literal["approval", "input"]
    id: str


class StateData(TypedDict, total=False):
    state: SessionState
    phase: str
    waiting_for: WaitingFor
    outcome: Outcome
    provider_thinking: bool


AGENT_API_CHANNEL = "agent_api"
SESSION_KEY_PREFIX = f"{AGENT_API_CHANNEL}:"


def now_ms() -> int:
    return int(time.time() * 1000)


def session_key_for(session_id: str) -> str:
    return f"{SESSION_KEY_PREFIX}{session_id}"


def session_id_for_key(session_key: str) -> str:
    """Map an internal session key to the public session id (identity for other channels)."""
    if session_key.startswith(SESSION_KEY_PREFIX):
        return session_key[len(SESSION_KEY_PREFIX):]
    return session_key


# ---------------------------------------------------------------------------
# data builders
# ---------------------------------------------------------------------------


def delta_data(text: str) -> JsonObject:
    return {"text": text}


def state_data(
    state: SessionState,
    *,
    phase: str | None = None,
    waiting_for: WaitingFor | None = None,
    outcome: Outcome | None = None,
    provider_thinking: bool = False,
) -> JsonObject:
    data: JsonObject = {"state": state}
    if phase is not None:
        data["phase"] = phase
    if waiting_for is not None:
        data["waiting_for"] = dict(waiting_for)
    if outcome is not None:
        data["outcome"] = outcome
    if provider_thinking:
        data["provider_thinking"] = True
    return data


def tool_data(
    event: Literal["started", "finished", "failed"],
    *,
    name: str,
    call_id: str,
    summary: str | None = None,
    duration_ms: int | None = None,
    display: str | None = None,
    arguments: str | None = None,
) -> JsonObject:
    data: JsonObject = {"event": event, "name": name, "call_id": call_id}
    if summary is not None:
        data["summary"] = summary
    if duration_ms is not None:
        data["duration_ms"] = duration_ms
    if display is not None:
        data["display"] = display
    if arguments is not None:
        data["arguments"] = arguments
    return data


def subagent_data(
    event: Literal["started", "finished", "failed"],
    *,
    id: str,
    role: str,
    summary: str | None = None,
    duration_ms: int | None = None,
    display: str | None = None,
) -> JsonObject:
    data: JsonObject = {"event": event, "id": id, "role": role}
    if summary is not None:
        data["summary"] = summary
    if duration_ms is not None:
        data["duration_ms"] = duration_ms
    if display:
        data["display"] = display
    return data


def structured_data(type: str, result_id: str, payload: JsonObject) -> JsonObject:
    return {"type": type, "result_id": result_id, "payload": payload}


def artifact_data(artifact_id: str, mime: str, url: str, title: str) -> JsonObject:
    return {"artifact_id": artifact_id, "mime": mime, "url": url, "title": title}


def approval_data(
    approval_id: str,
    *,
    type: str,
    summary: str,
    expires_at: int | None,
    status: str,
    actions: tuple[str, ...] = ("confirm", "cancel"),
) -> JsonObject:
    return {
        "approval_id": approval_id,
        "type": type,
        "summary": summary,
        "expires_at": expires_at,
        "status": status,
        "actions": list(actions),
    }


def notification_data(
    level: Literal["info", "warning", "error"],
    title_key: str,
    body_key: str,
    *,
    args: JsonObject | None = None,
    deep_link: str | None = None,
) -> JsonObject:
    data: JsonObject = {
        "level": level,
        "title": title_key,
        "body": body_key,
        "args": dict(args or {}),
    }
    if deep_link is not None:
        data["deep_link"] = deep_link
    return data


def job_data(
    job_id: str,
    *,
    kind: Literal["cron", "goal"],
    status: str,
    progress: JsonObject | None = None,
    next_run_at: int | None = None,
) -> JsonObject:
    data: JsonObject = {"job_id": job_id, "kind": kind, "status": status}
    if progress is not None:
        data["progress"] = progress
    if next_run_at is not None:
        data["next_run_at"] = next_run_at
    return data


def end_data(run: str | None, outcome: Outcome) -> JsonObject:
    return {"run": run, "outcome": outcome}


# ---------------------------------------------------------------------------
# translators from runtime events
# ---------------------------------------------------------------------------


class Translated(TypedDict):
    session: str
    kind: EventKind
    data: JsonObject


def outcome_from_turn(event: TurnCompleted) -> Outcome:
    if event.outcome == "completed":
        return "ok"
    if event.outcome == "cancelled":
        return "cancelled"
    return "error"


def phase_from_status(status: str) -> str:
    if status == "running":
        return "streaming"
    return status


def translate_runtime_event(event: AgentEvent) -> Translated | None:
    """Translate a bus event into a public event payload (07 §3), or ``None`` to ignore."""
    if isinstance(event, UserInputAccepted):
        session = session_id_for_key(event.context.session_key)
        return {"session": session, "kind": "state", "data": state_data("working", phase="queued")}
    if isinstance(event, SessionTurnStarted):
        session = session_id_for_key(event.context.session_key)
        return {
            "session": session,
            "kind": "state",
            "data": state_data("working", phase="processing"),
        }
    if isinstance(event, TurnRuntimeAdmitted):
        session = session_id_for_key(event.context.session_key)
        return {
            "session": session,
            "kind": "state",
            "data": state_data("working", phase="processing"),
        }
    if isinstance(event, TurnRunStatusChanged):
        if event.status == "idle":
            return None
        session = session_id_for_key(event.context.session_key)
        return {
            "session": session,
            "kind": "state",
            "data": state_data("working", phase=phase_from_status(event.status)),
        }
    if isinstance(event, TurnCompleted):
        session = session_id_for_key(event.context.session_key)
        return {
            "session": session,
            "kind": "state",
            "data": state_data("completed", outcome=outcome_from_turn(event)),
        }
    if isinstance(event, TeamRoleEvent):
        if not event.session_key:
            return None
        stage: Literal["started", "finished", "failed"] = {
            "running": "started",
            "done": "finished",
            "failed": "failed",
        }[event.status]
        return {
            "session": session_id_for_key(event.session_key),
            "kind": "subagent",
            "data": subagent_data(
                stage,
                id=event.agent_id,
                role=event.role,
                summary=event.summary or None,
                duration_ms=event.duration_ms,
                display=event.display or None,
            ),
        }
    if isinstance(event, DecisionCompletedEvent):
        if not event.session_key:
            return None
        return {
            "session": session_id_for_key(event.session_key),
            "kind": "structured",
            "data": structured_data("decision", "", dict(event.payload)),
        }
    if isinstance(event, RetryStatusEvent):
        if not event.session_key:
            return None
        data: JsonObject = {
            "state": event.state,
            "attempt": event.attempt,
            "error_kind": event.error_kind,
        }
        if event.max_attempts is not None:
            data["max_attempts"] = event.max_attempts
        return {
            "session": session_id_for_key(event.session_key),
            "kind": "retry",
            "data": data,
        }
    if isinstance(event, GoalStateChanged):
        session = session_id_for_key(event.context.session_key)
        blob = goal_state_ws_blob(event.session_metadata)
        status = str(blob.get("status") or ("active" if blob.get("active") else "inactive"))
        progress: JsonObject = {}
        summary = blob.get("ui_summary")
        if isinstance(summary, str):
            progress["summary"] = summary
        recap = blob.get("recap")
        if isinstance(recap, str):
            progress["recap"] = recap
        return {
            "session": session,
            "kind": "job",
            "data": job_data(
                f"goal:{event.context.session_key}",
                kind="goal",
                status=status,
                progress=progress or None,
            ),
        }
    return None
