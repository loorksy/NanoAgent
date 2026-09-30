"""Working / Waiting / Completed derivation per session (07 §3)."""

from __future__ import annotations

import time
from typing import TypedDict, cast

from mokli.agent_api.events import (
    JsonObject,
    Outcome,
    SessionState,
    StateData,
    WaitingFor,
    state_data,
)


class SessionStateSnapshot(TypedDict):
    session: str
    state: SessionState
    phase: str | None
    waiting_for: WaitingFor | None
    outcome: Outcome | None
    run: str | None
    updated_at: int


class StateTracker:
    """Pure state machine; the hub feeds it and emits ``state`` events on change."""

    def __init__(self) -> None:
        self._states: dict[str, SessionStateSnapshot] = {}
        self._pending_approvals: dict[str, list[str]] = {}
        self._active_runs: dict[str, str] = {}

    # -- queries ---------------------------------------------------------

    def snapshot(self, session: str) -> SessionStateSnapshot:
        found = self._states.get(session)
        if found is not None:
            return found
        return {
            "session": session,
            "state": "completed",
            "phase": None,
            "waiting_for": None,
            "outcome": None,
            "run": None,
            "updated_at": 0,
        }

    def active_run(self, session: str) -> str | None:
        return self._active_runs.get(session)

    def pending_approvals(self, session: str) -> list[str]:
        return list(self._pending_approvals.get(session, ()))

    def is_waiting(self, session: str) -> bool:
        return bool(self._pending_approvals.get(session))

    # -- transitions -----------------------------------------------------

    def run_started(self, session: str, run: str) -> StateData:
        self._active_runs[session] = run
        return self._set(session, "working", phase="queued", run=run)

    def working(self, session: str, *, phase: str) -> StateData | None:
        current = self.snapshot(session)
        if current["state"] == "working" and current["phase"] == phase:
            return None
        return self._set(session, "working", phase=phase, run=current["run"])

    def run_finished(self, session: str, run: str | None, outcome: Outcome) -> StateData | None:
        active = self._active_runs.get(session)
        if run is not None and active is not None and active != run:
            return None
        self._active_runs.pop(session, None)
        pending = self._pending_approvals.get(session)
        if pending and outcome == "ok":
            return self._set(
                session,
                "waiting",
                waiting_for={"kind": "approval", "id": pending[0]},
                run=run,
            )
        return self._set(session, "completed", outcome=outcome, run=run)

    def approval_opened(self, session: str, approval_id: str) -> StateData | None:
        pending = self._pending_approvals.setdefault(session, [])
        if approval_id not in pending:
            pending.append(approval_id)
        if self.active_run(session) is not None:
            return None
        return self._set(
            session,
            "waiting",
            waiting_for={"kind": "approval", "id": approval_id},
            run=self.snapshot(session)["run"],
        )

    def approval_resolved(
        self,
        session: str,
        approval_id: str,
        *,
        outcome: Outcome,
    ) -> StateData | None:
        pending = self._pending_approvals.get(session)
        if pending and approval_id in pending:
            pending.remove(approval_id)
        if pending:
            return self._set(
                session,
                "waiting",
                waiting_for={"kind": "approval", "id": pending[0]},
                run=self.snapshot(session)["run"],
            )
        self._pending_approvals.pop(session, None)
        if self.active_run(session) is not None:
            # The run is still open. That is not a provider thinking signal.
            return self._set(
                session, "working", phase="processing", run=self.active_run(session),
            )
        return self._set(session, "completed", outcome=outcome, run=self.snapshot(session)["run"])

    # -- internals -------------------------------------------------------

    def _set(
        self,
        session: str,
        state: SessionState,
        *,
        phase: str | None = None,
        waiting_for: WaitingFor | None = None,
        outcome: Outcome | None = None,
        run: str | None,
    ) -> StateData:
        self._states[session] = {
            "session": session,
            "state": state,
            "phase": phase,
            "waiting_for": waiting_for,
            "outcome": outcome,
            "run": run,
            "updated_at": int(time.time() * 1000),
        }
        data = state_data(state, phase=phase, waiting_for=waiting_for, outcome=outcome)
        return _as_state_data(data)


def _as_state_data(data: JsonObject) -> StateData:
    out: StateData = {"state": _state_value(data.get("state"))}
    phase = data.get("phase")
    if isinstance(phase, str):
        out["phase"] = phase
    waiting = data.get("waiting_for")
    if isinstance(waiting, dict):
        waiting_map = cast(JsonObject, waiting)
        kind = waiting_map.get("kind")
        ident = waiting_map.get("id")
        wf: WaitingFor = {}
        if kind in ("approval", "input"):
            wf["kind"] = kind
        if isinstance(ident, str):
            wf["id"] = ident
        out["waiting_for"] = wf
    outcome = data.get("outcome")
    if outcome in ("ok", "cancelled", "error", "expired"):
        out["outcome"] = outcome
    return out


def _state_value(value: object) -> SessionState:
    if value == "working":
        return "working"
    if value == "waiting":
        return "waiting"
    return "completed"
