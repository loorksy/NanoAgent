"""Decide per event: deliver over a live WS/SSE subscription only, or push to devices."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import cast

from loguru import logger

from mokli.agent_api.devices import DeviceRegistry
from mokli.agent_api.events import GatewayEvent, JsonObject
from mokli.agent_api.hub import EventHub
from mokli.agent_api.push.base import LoggingPushProvider, PushPayload, PushProvider

PUSH_KINDS: frozenset[str] = frozenset({"approval", "notification", "structured", "job"})
SilenceGate = Callable[[GatewayEvent], bool]


def payload_for(event: GatewayEvent) -> PushPayload | None:
    """Translate a public event into a key-only push payload (07 §7), or ``None`` to skip."""
    kind = event["kind"]
    data = event["data"]
    session = event["session"]
    if kind == "approval":
        if data.get("status") not in (None, "pending"):
            return None
        approval_id = data.get("approval_id")
        return {
            "kind": "approval",
            "title_key": "push.approval.title",
            "body_key": "push.approval.body",
            "args": {"type": data.get("type")},
            "session": session,
            "deep_link": f"mokli://approvals/{approval_id}",
            "approval_id": str(approval_id) if isinstance(approval_id, str) else None,
        }
    if kind == "notification":
        return {
            "kind": "notification",
            "title_key": str(data.get("title") or "push.notification.title"),
            "body_key": str(data.get("body") or "push.notification.body"),
            "args": {"level": data.get("level")},
            "session": session,
            "deep_link": str(data.get("deep_link") or f"mokli://sessions/{session}"),
            "approval_id": None,
        }
    if kind == "structured" and data.get("type") == "decision":
        payload = data.get("payload")
        verdict = cast(JsonObject, payload).get("verdict") if isinstance(payload, dict) else None
        return {
            "kind": "decision",
            "title_key": "push.decision.title",
            "body_key": "push.decision.body",
            "args": {"verdict": verdict, "result_id": data.get("result_id")},
            "session": session,
            "deep_link": f"mokli://results/{data.get('result_id')}",
            "approval_id": None,
        }
    if kind == "job" and data.get("status") in ("finished", "failed", "error"):
        return {
            "kind": "job",
            "title_key": "push.job.title",
            "body_key": f"push.job.{data.get('status')}",
            "args": {"job_id": data.get("job_id"), "kind": data.get("kind")},
            "session": session,
            "deep_link": f"mokli://jobs/{data.get('job_id')}",
            "approval_id": None,
        }
    return None


class PushRouter:
    def __init__(
        self,
        hub: EventHub,
        devices: DeviceRegistry,
        providers: list[PushProvider] | None = None,
        *,
        silence_gate: SilenceGate | None = None,
        connected: Callable[[], bool] | None = None,
    ) -> None:
        self._hub = hub
        self._devices = devices
        self._providers: list[PushProvider] = providers or [LoggingPushProvider()]
        self._silence = silence_gate
        self._connected = connected
        self._tasks: set[asyncio.Task[int]] = set()
        self._detach: Callable[[], None] | None = None

    def attach(self) -> None:
        if self._detach is None:
            self._detach = self._hub.add_global_listener(self.on_event)

    def detach(self) -> None:
        if self._detach is not None:
            self._detach()
            self._detach = None

    def on_event(self, event: GatewayEvent) -> None:
        if event["kind"] not in PUSH_KINDS:
            return
        payload = payload_for(event)
        if payload is None:
            return
        if self._silence is not None and self._silence(event):
            return
        if self._connected is not None and self._connected():
            return
        if self._hub.has_listeners(event["session"]):
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        task = loop.create_task(self.deliver(payload))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def deliver(self, payload: PushPayload) -> int:
        delivered = 0
        for device in self._devices.list():
            for provider in self._providers:
                if not provider.supports(device):
                    continue
                try:
                    if await provider.send(device, payload):
                        delivered += 1
                        break
                except Exception:
                    logger.exception("agent_api push provider {} failed", provider.name)
        return delivered

    async def wait_idle(self) -> None:
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
