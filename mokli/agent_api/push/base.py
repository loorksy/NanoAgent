"""Push provider contract. Payloads carry keys and ids only — never prices or levels."""

from __future__ import annotations

from typing import Protocol, TypedDict

from loguru import logger

from mokli.agent_api.devices import DeviceRecord
from mokli.agent_api.events import JsonObject


class PushPayload(TypedDict):
    kind: str
    title_key: str
    body_key: str
    args: JsonObject
    session: str | None
    deep_link: str
    approval_id: str | None


class PushProvider(Protocol):
    name: str

    def supports(self, device: DeviceRecord) -> bool: ...

    async def send(self, device: DeviceRecord, payload: PushPayload) -> bool: ...


class LoggingPushProvider:
    """Default provider: records deliveries in the log (and in memory for tests)."""

    name = "logging"

    def __init__(self) -> None:
        self.sent: list[tuple[str, PushPayload]] = []

    def supports(self, device: DeviceRecord) -> bool:
        return True

    async def send(self, device: DeviceRecord, payload: PushPayload) -> bool:
        self.sent.append((device["id"], payload))
        logger.info(
            "agent_api push (no provider configured) device={} kind={} title={}",
            device["id"],
            payload["kind"],
            payload["title_key"],
        )
        return True
