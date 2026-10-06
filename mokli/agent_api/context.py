"""Service container shared by all route modules through ``request.app``."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aiohttp import web

from mokli.agent_api.approvals import ApprovalRegistry
from mokli.agent_api.auth import TokenStore
from mokli.agent_api.config import AgentApiConfig
from mokli.agent_api.db import Database
from mokli.agent_api.devices import DeviceRegistry
from mokli.agent_api.event_log import EventLog
from mokli.agent_api.hub import EventHub
from mokli.agent_api.jobs import JobsService
from mokli.agent_api.push.router import PushRouter
from mokli.agent_api.results import ResultsStore
from mokli.agent_api.sessions import SessionService


@dataclass
class ConnectionTracker:
    """Live WS connections, consulted by the push router ("WS connected → no push")."""

    clients: set[str] = field(default_factory=set)
    _counts: dict[str, int] = field(default_factory=dict)

    def connected(self, client_id: str) -> None:
        self._counts[client_id] = self._counts.get(client_id, 0) + 1
        self.clients.add(client_id)

    def disconnected(self, client_id: str) -> None:
        remaining = self._counts.get(client_id, 0) - 1
        if remaining <= 0:
            self._counts.pop(client_id, None)
            self.clients.discard(client_id)
        else:
            self._counts[client_id] = remaining

    def any_connected(self) -> bool:
        return bool(self.clients)


@dataclass
class AgentApiServices:
    config: AgentApiConfig
    db: Database
    event_log: EventLog
    hub: EventHub
    sessions: SessionService
    approvals: ApprovalRegistry
    jobs: JobsService
    results: ResultsStore
    tokens: TokenStore
    devices: DeviceRegistry
    push: PushRouter
    connections: ConnectionTracker = field(default_factory=ConnectionTracker)
    # Root mokli config file; ``None`` means "use the process default path".
    config_path: Path | None = None
    # In-memory OAuth attempts for provider connect. Never persisted.
    oauth_flows: Any = None


SERVICES_KEY = web.AppKey[AgentApiServices]("agent_api_services")


def services(request: web.Request) -> AgentApiServices:
    return request.app[SERVICES_KEY]
