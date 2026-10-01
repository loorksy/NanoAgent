"""Sessions: auth, submit, SSE stream, timeline, state, cancel."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path

import pytest
from aiohttp.test_utils import TestClient

from agent_api.conftest import BOOTSTRAP, FakeAgent, auth, parse_sse
from mokli.agent.tools.context import RequestContext, bind_request_context, reset_request_context
from mokli.agent_api.context import AgentApiServices
from mokli.agent_api.events import AGENT_API_CHANNEL, session_key_for
from mokli.trading.locale import active_locale


async def test_requires_bearer_token(client: TestClient) -> None:
    resp = await client.get("/api/v2/sessions")
    assert resp.status == 401
    body = await resp.json()
    assert body["error"]["code"] == "unauthorized"


async def test_health_is_public(client: TestClient) -> None:
    resp = await client.get("/api/v2/health")
    assert resp.status == 200
    assert (await resp.json())["ok"] is True


async def test_me_reports_bootstrap_scopes(client: TestClient) -> None:
    resp = await client.get("/api/v2/me", headers=auth())
    assert resp.status == 200
    body = await resp.json()
    assert body["kind"] == "service"
    assert "admin" in body["scopes"]
    assert body["dir"] == "ltr"


async def test_cors_preflight_echoes_allowed_origin(client: TestClient) -> None:
    resp = await client.options(
        "/api/v2/sessions",
        headers={"Origin": "http://mokli.local", "Access-Control-Request-Method": "POST"},
    )
    assert resp.status == 204
    assert resp.headers["Access-Control-Allow-Origin"] == "http://mokli.local"
    denied = await client.options("/api/v2/sessions", headers={"Origin": "http://evil.example"})
    assert "Access-Control-Allow-Origin" not in denied.headers


async def test_submit_streams_delta_and_end(client: TestClient, agent: FakeAgent) -> None:
    created = await client.post("/api/v2/sessions", json={"title": "gold"}, headers=auth())
    assert created.status == 201
    session = (await created.json())["id"]

    accepted = await client.post(
        f"/api/v2/sessions/{session}/messages", json={"text": "analyse gold"}, headers=auth(),
    )
    assert accepted.status == 202
    run_id = (await accepted.json())["run_id"]

    stream = await client.get(
        f"/api/v2/sessions/{session}/events?until_end=1&keepalive=0.2", headers=auth(),
    )
    assert stream.status == 200
    assert stream.headers["Content-Type"].startswith("text/event-stream")
    events = parse_sse(await stream.text())

    kinds = [event["kind"] for event in events]
    assert kinds[0] == "state"
    assert "delta" in kinds
    assert kinds[-1] == "end"
    assert events[-1]["data"] == {"run": run_id, "outcome": "ok"}
    assert "".join(e["data"]["text"] for e in events if e["kind"] == "delta").strip() == agent.reply
    ids = [event["id"] for event in events]
    assert ids == sorted(ids)

    call = agent.calls[0]
    assert call["session_key"] == session_key_for(session)
    assert call["channel"] == AGENT_API_CHANNEL
    assert call["chat_id"] == session


async def test_sse_diagnostic_matches_section11_extract(
    client: TestClient,
    agent: FakeAgent,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When turn diagnostics exist, SSE publishes ``diagnostic`` for §11 scripts."""
    measured = {
        "rounds": 2,
        "request_input_tokens": 1200,
        "request_output_tokens": 90,
        "tool_calls": 1,
        "context_ms": 30,
        "model_ms": 800,
        "provider_tool_count": 3,
    }
    monkeypatch.setattr(
        "mokli.agent_api.sessions.latest_diagnostics",
        lambda _key: measured,
    )
    session = (await (await client.post("/api/v2/sessions", headers=auth())).json())["id"]
    await client.post(
        f"/api/v2/sessions/{session}/messages",
        json={"text": "hello"},
        headers=auth(),
    )
    events = parse_sse(
        await (
            await client.get(
                f"/api/v2/sessions/{session}/events?until_end=1",
                headers=auth(),
            )
        ).text()
    )
    diagnostic_events = [event for event in events if event["kind"] == "diagnostic"]
    assert len(diagnostic_events) == 1
    gateway_event = diagnostic_events[0]
    assert gateway_event["data"] == measured

    script = Path(__file__).resolve().parents[2] / "scripts" / "mokli_upgrade_diagnostic_extract.py"
    proc = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(gateway_event),
        capture_output=True,
        text=True,
        check=True,
    )
    summary = proc.stdout.strip()
    assert "rounds=2" in summary
    assert "in=1200" in summary
    assert "tools=1" in summary
    assert "provider_tools=3" in summary


async def test_timeline_excludes_deltas_and_supports_after(client: TestClient) -> None:
    session = (await (await client.post("/api/v2/sessions", headers=auth())).json())["id"]
    await client.post(f"/api/v2/sessions/{session}/messages", json={"text": "hi"}, headers=auth())
    await (await client.get(f"/api/v2/sessions/{session}/events?until_end=1", headers=auth())).text()

    resp = await client.get(f"/api/v2/sessions/{session}/timeline", headers=auth())
    events = (await resp.json())["events"]
    assert events and all(event["kind"] != "delta" for event in events)
    assert events[-1]["kind"] == "end"

    after = events[0]["id"]
    tail = (await (await client.get(
        f"/api/v2/sessions/{session}/timeline?after={after}", headers=auth(),
    )).json())["events"]
    assert [event["id"] for event in tail] == [event["id"] for event in events[1:]]


async def test_sse_resume_with_last_event_id(client: TestClient) -> None:
    session = (await (await client.post("/api/v2/sessions", headers=auth())).json())["id"]
    await client.post(f"/api/v2/sessions/{session}/messages", json={"text": "hi"}, headers=auth())
    first = parse_sse(await (await client.get(
        f"/api/v2/sessions/{session}/events?until_end=1", headers=auth(),
    )).text())
    cursor = first[1]["id"]
    resumed = parse_sse(await (await client.get(
        f"/api/v2/sessions/{session}/events?until_end=1",
        headers={**auth(), "Last-Event-ID": cursor},
    )).text())
    assert [event["id"] for event in resumed] == [event["id"] for event in first[2:]]


async def test_state_and_cancel_mid_turn(
    client: TestClient, agent: FakeAgent, services: AgentApiServices,
) -> None:
    agent.block = asyncio.Event()
    session = (await (await client.post("/api/v2/sessions", headers=auth())).json())["id"]
    await client.post(f"/api/v2/sessions/{session}/messages", json={"text": "hi"}, headers=auth())
    await asyncio.sleep(0.05)

    state = await (await client.get(f"/api/v2/sessions/{session}/state", headers=auth())).json()
    assert state["state"] == "working"

    busy = await client.post(
        f"/api/v2/sessions/{session}/messages", json={"text": "again"}, headers=auth(),
    )
    assert busy.status == 409

    cancelled = await client.post(f"/api/v2/sessions/{session}/cancel", headers=auth())
    body = await cancelled.json()
    assert body["cancelled"] is True
    assert body["state"]["state"] == "completed"
    assert body["state"]["outcome"] == "cancelled"
    assert agent.cancelled_keys == [session_key_for(session)]

    timeline = services.sessions.timeline(session)
    assert timeline[-1]["kind"] == "end"
    assert timeline[-1]["data"]["outcome"] == "cancelled"


async def test_agent_error_ends_run_with_error_outcome(client: TestClient, agent: FakeAgent) -> None:
    agent.raise_error = True
    session = (await (await client.post("/api/v2/sessions", headers=auth())).json())["id"]
    await client.post(f"/api/v2/sessions/{session}/messages", json={"text": "hi"}, headers=auth())
    events = parse_sse(await (await client.get(
        f"/api/v2/sessions/{session}/events?until_end=1", headers=auth(),
    )).text())
    assert events[-1]["kind"] == "end"
    assert events[-1]["data"]["outcome"] == "error"


async def test_busy_run_does_not_change_the_selected_model(
    client: TestClient, agent: FakeAgent,
) -> None:
    agent.block = asyncio.Event()
    session = (await (await client.post("/api/v2/sessions", headers=auth())).json())["id"]
    await client.post(f"/api/v2/sessions/{session}/messages", json={"text": "hi"}, headers=auth())
    await asyncio.sleep(0.05)

    busy = await client.post(
        f"/api/v2/sessions/{session}/messages",
        json={"text": "again", "model": None},
        headers=auth(),
    )
    assert busy.status == 409
    assert agent.cleared == []
    agent.block.set()


async def test_failed_model_clear_does_not_start_the_turn(
    client: TestClient, agent: FakeAgent,
) -> None:
    agent.fail_clear = True
    session = (await (await client.post("/api/v2/sessions", headers=auth())).json())["id"]
    resp = await client.post(
        f"/api/v2/sessions/{session}/messages",
        json={"text": "hi", "model": None},
        headers=auth(),
    )
    assert resp.status == 500
    assert (await resp.json())["error"]["code"] == "model_clear_failed"
    assert agent.calls == []


async def test_empty_message_rejected(client: TestClient) -> None:
    session = (await (await client.post("/api/v2/sessions", headers=auth())).json())["id"]
    resp = await client.post(f"/api/v2/sessions/{session}/messages", json={"text": "  "}, headers=auth())
    assert resp.status == 400
    assert (await resp.json())["error"]["code"] == "empty_message"


async def test_delete_archives_session(client: TestClient) -> None:
    session = (await (await client.post("/api/v2/sessions", headers=auth())).json())["id"]
    assert (await client.delete(f"/api/v2/sessions/{session}", headers=auth())).status == 200
    listed = (await (await client.get("/api/v2/sessions", headers=auth())).json())["sessions"]
    assert all(record["id"] != session for record in listed)
    archived = (await (await client.get(
        "/api/v2/sessions?archived=1", headers=auth(),
    )).json())["sessions"]
    assert any(record["id"] == session and record["archived"] for record in archived)
    missing = await client.delete("/api/v2/sessions/nope", headers=auth())
    assert missing.status == 404


async def test_scope_enforced_for_web_token(client: TestClient, services: AgentApiServices) -> None:
    issued = services.tokens.issue("service", scopes=["read"], label="dashboard")
    resp = await client.post("/api/v2/sessions", headers=auth(issued["token"]))
    assert resp.status == 403
    body = await resp.json()
    assert body["error"]["message_key"] == "auth.missing_scope"
    assert body["error"]["details"]["scope"] == "chat"
    assert (await client.get("/api/v2/sessions", headers=auth(issued["token"]))).status == 200
    assert BOOTSTRAP != issued["token"]


async def test_message_attachments_saved_as_media(
    client: TestClient, agent: FakeAgent, monkeypatch,
) -> None:
    from mokli.agent_api.routes import sessions as sessions_routes

    saved: list[str] = []

    def fake_save(url: str, media_dir: object) -> str:
        saved.append(url[:12])
        return f"/tmp/{len(saved)}.png"

    monkeypatch.setattr("mokli.api.server._save_base64_data_url", fake_save)
    assert sessions_routes.MEDIA_SUBDIR == "agent_api"
    session = (await (await client.post("/api/v2/sessions", headers=auth())).json())["id"]
    png = "data:image/png;base64,iVBORw0KGgo="
    resp = await client.post(
        f"/api/v2/sessions/{session}/messages",
        json={"content": "look", "attachments": [{"type": "image", "url": png}], "media": [png]},
        headers=auth(),
    )
    assert resp.status == 202
    await (await client.get(f"/api/v2/sessions/{session}/events?until_end=1", headers=auth())).text()
    assert agent.calls[0]["media"] == ["/tmp/1.png", "/tmp/2.png"]
    assert saved == ["data:image/p", "data:image/p"]


def test_ui_locale_overrides_the_script_of_the_message() -> None:
    token = bind_request_context(RequestContext(
        channel="agent_api",
        chat_id="chat",
        original_user_text="hello",
        attributes={"locale": "ar-BH"},
    ))
    try:
        assert active_locale("hello") == "ar"
    finally:
        reset_request_context(token)
    assert active_locale("hello") == "en"


async def test_chat_scope_can_cancel_and_locale_reaches_the_turn(
    client: TestClient, agent: FakeAgent, services: AgentApiServices,
) -> None:
    issued = services.tokens.issue("service", scopes=["chat"], label="pipe")
    headers = auth(issued["token"])
    session = (await (await client.post("/api/v2/sessions", headers=headers)).json())["id"]
    posted = await client.post(
        f"/api/v2/sessions/{session}/messages",
        json={"text": "hi", "locale": "ar-BH"},
        headers=headers,
    )
    assert posted.status == 202
    await asyncio.sleep(0.05)
    assert agent.calls[0]["attributes"] == {"locale": "ar-BH"}

    agent.block = asyncio.Event()
    await client.post(
        f"/api/v2/sessions/{session}/messages", json={"text": "again"}, headers=headers,
    )
    await asyncio.sleep(0.05)
    cancelled = await client.post(f"/api/v2/sessions/{session}/cancel", headers=headers)
    assert cancelled.status == 200
    assert (await cancelled.json())["cancelled"] is True


async def test_openai_compat_routes_share_listener_and_auth(client: TestClient, agent: FakeAgent) -> None:
    assert (await client.get("/v1/models")).status == 401
    models = await (await client.get("/v1/models", headers=auth())).json()
    assert [m["id"] for m in models["data"]] == ["mokli"]

    resp = await client.post(
        "/v1/chat/completions",
        json={"model": "mokli", "messages": [{"role": "user", "content": "hi"}]},
        headers={**auth(), "X-Mokliui-Chat-Id": "chat-42"},
    )
    assert resp.status == 200
    body = await resp.json()
    assert body["choices"][0]["message"]["content"].strip() == agent.reply
    assert agent.calls[0]["session_key"] == "api:chat-42"
