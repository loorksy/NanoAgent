"""The tasks page must not scan session message lines on the event loop."""

from __future__ import annotations

import asyncio
import json
import threading
import time
from pathlib import Path

from aiohttp.test_utils import TestClient, TestServer

from agent_api.conftest import BOOTSTRAP, FakeAgent, auth
from mokli.agent_api.app import AgentApiDeps, create_app
from mokli.agent_api.config import AgentApiConfig
from mokli.agent_api.jobs import JobsService
from mokli.session.manager import SessionManager


def _session(manager: SessionManager, key: str, *, goal: bool) -> None:
    session = manager.get_or_create(key)
    if goal:
        session.metadata["goal_state"] = {
            "status": "active",
            "objective": "watch gold",
            "ui_summary": "Watch gold",
        }
    session.add_message("user", "kept")
    session.add_message("assistant", "x" * 80_000)
    manager.save(session)


def test_task_list_reads_the_metadata_line_only(tmp_path: Path, monkeypatch) -> None:
    manager = SessionManager(tmp_path / "workspace", sessions_root=tmp_path / "sessions")
    _session(manager, "websocket:desk", goal=True)
    _session(manager, "websocket:quiet", goal=False)
    loads: list[int] = []
    real_loads = json.loads

    def counting(text: str, *args: object, **kwargs: object) -> object:
        loads.append(len(text))
        return real_loads(text, *args, **kwargs)

    monkeypatch.setattr("mokli.session.manager.json.loads", counting)
    service = JobsService(None, manager)
    jobs = service.list()
    goals = [job for job in jobs if job["kind"] == "goal"]
    assert [job["name"] for job in goals] == ["Watch gold"]
    assert goals[0]["job_id"] == "goal:websocket:desk"
    found = service.get("goal:websocket:desk")
    assert found is not None
    assert found["name"] == "Watch gold"
    assert loads
    assert max(loads) < 80_000


async def test_task_list_leaves_the_event_loop_free(tmp_path: Path, monkeypatch) -> None:
    manager = SessionManager(tmp_path / "workspace", sessions_root=tmp_path / "sessions")
    _session(manager, "websocket:desk", goal=True)
    _session(manager, "websocket:quiet", goal=False)
    order: list[str] = []
    loads: list[int] = []
    real_loads = json.loads
    real_list = manager.list_session_metadata

    def counting(text: str, *args: object, **kwargs: object) -> object:
        loads.append(len(text))
        return real_loads(text, *args, **kwargs)

    def slow() -> list[dict[str, object]]:
        time.sleep(0.2)
        order.append(
            "main" if threading.current_thread() is threading.main_thread() else "worker"
        )
        return real_list()

    monkeypatch.setattr("mokli.session.manager.json.loads", counting)
    monkeypatch.setattr(manager, "list_session_metadata", slow)
    deps = AgentApiDeps(
        session_manager=manager,
        config_path=tmp_path / "config.json",
        db_path=tmp_path / "events.sqlite",
    )
    app = create_app(
        FakeAgent(),
        AgentApiConfig(host="127.0.0.1", port=0, bootstrap_token=BOOTSTRAP),
        tmp_path / "workspace",
        deps,
    )
    client = TestClient(TestServer(app))
    await client.start_server()
    try:
        loads.clear()

        async def tick() -> None:
            await asyncio.sleep(0.05)
            order.append("tick")

        pending = asyncio.create_task(tick())
        started = time.perf_counter()
        response = await client.get("/api/v2/tasks", headers=auth())
        await pending
        assert response.status == 200
        body = await response.json()
        assert order[0] == "tick"
        assert "main" not in order
        assert order.count("worker") == 1
        assert time.perf_counter() - started < 0.35
        goals = [job for job in body["jobs"] if job["kind"] == "goal"]
        assert [job["name"] for job in goals] == ["Watch gold"]
        assert loads
        assert max(loads) < 80_000
    finally:
        await client.close()
