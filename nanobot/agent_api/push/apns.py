"""APNs provider placeholder: reports ``not configured`` until a ``.p8`` key is wired."""

from __future__ import annotations

from loguru import logger

from nanobot.agent_api.devices import DeviceRecord
from nanobot.agent_api.push.base import PushPayload


class ApnsProvider:
    name = "apns"

    def __init__(self, *, key_id: str = "", team_id: str = "", bundle_id: str = "") -> None:
        self.key_id = key_id
        self.team_id = team_id
        self.bundle_id = bundle_id

    @property
    def configured(self) -> bool:
        return False

    def supports(self, device: DeviceRecord) -> bool:
        return device["platform"] == "ios"

    async def send(self, device: DeviceRecord, payload: PushPayload) -> bool:
        logger.info("agent_api apns not configured; skipped push for device {}", device["id"])
        return False
