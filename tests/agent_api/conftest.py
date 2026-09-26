"""Shared fixtures: a fake ``AgentLoop`` and an in-process Agent API test client."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from aiohttp.test_utils import TestClient, TestServer

from nanobot.agent.tools.registry import ToolRegistry
from nanobot.agent_api.app import AgentApiDeps, create_app
from nanobot.agent_api.config import AgentApiConfig
from nanobot.agent_api.context import SERVICES_KEY, AgentApiServices
from nanobot.security.secret_store import SecretStore, set_secret_store_for_tests
from nanobot.trading.permissions.store import PermissionStore, set_permission_store_for_tests
from nanobot.trading.policy import invalidate_live_cache

BOOTSTRAP = "nbat_test-bootstrap-token"


class FakeAgent:
    """Streams a scripted reply; optionally blocks so ``cancel`` can be exercised."""

    def __init__(self) -> None:
        self.tools = ToolRegistry()
        self.calls: list[dict[str, Any]] = []
        self.presets: list[tuple[str, str]] = []
        self.reply = "hello from agent"
        self.block: asyncio.Event | None = None
        self.raise_error = False
        self.cancelled_keys: list[str] = []

    def set_session_model_preset(self, session_key: str, name: str) -> None:
        self.presets.append((session_key, name))

    async def process_direct(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        on_stream: Callable[[str], Awaitable[None]] | None = kwargs.get("on_stream")
        if self.raise_error:
            raise RuntimeError("boom")
        if self.block is not None:
            await self.block.wait()
        if on_stream is not None:
            for token in self.reply.split(" "):
                await on_stream(token + " ")
        return SimpleNamespace(content=self.reply)

    async def _cancel_active_tasks(self, key: str) -> int:
        self.cancelled_keys.append(key)
        return 0


@pytest.fixture(autouse=True)
def _isolate_stores(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("nanobot.config.loader._current_config_path", tmp_path / "config.json")
    set_secret_store_for_tests(SecretStore(tmp_path / "secrets.enc"))
    set_permission_store_for_tests(PermissionStore(SecretStore(tmp_path / "secrets.enc")))
    monkeypatch.setattr("nanobot.trading.runtime_state._STORE", None)
    monkeypatch.setattr("nanobot.trading.risk_state._STORE", None)
    # ``/approvals`` syncs pending MT5 proposals from this process-global store, so
    # proposals left behind by other test modules in the same xdist worker must not leak in.
    monkeypatch.setattr("nanobot.trading.mt5_proposals._STORE", None)
    invalidate_live_cache()
    yield
    set_permission_store_for_tests(None)
    set_secret_store_for_tests(None)
    invalidate_live_cache()


@pytest.fixture
def agent() -> FakeAgent:
    return FakeAgent()


@pytest.fixture
def api_config() -> AgentApiConfig:
    return AgentApiConfig(
        host="127.0.0.1",
        port=0,
        bootstrap_token=BOOTSTRAP,
        cors_origins=["http://openwebui.local"],
        request_timeout_seconds=5.0,
    )


@pytest.fixture
async def client(
    agent: FakeAgent, api_config: AgentApiConfig, tmp_path: Path,
) -> AsyncIterator[TestClient]:
    deps = AgentApiDeps(config_path=tmp_path / "config.json")
    app = create_app(agent, api_config, tmp_path / "workspace", deps)
    server = TestServer(app)
    test_client = TestClient(server)
    await test_client.start_server()
    try:
        yield test_client
    finally:
        await test_client.close()


@pytest.fixture
def services(client: TestClient) -> AgentApiServices:
    return client.app[SERVICES_KEY]


def auth(token: str = BOOTSTRAP) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def parse_sse(raw: str) -> list[dict[str, Any]]:
    """Return the ``data`` payloads of every SSE frame in ``raw``."""
    events: list[dict[str, Any]] = []
    for block in raw.split("\n\n"):
        for line in block.splitlines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
    return events
