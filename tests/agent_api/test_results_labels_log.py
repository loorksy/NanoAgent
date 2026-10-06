"""Results (JSON + HTML), labels catalog, approvals REST and the merged operator log."""

from __future__ import annotations

import json

from aiohttp.test_utils import TestClient

from agent_api.conftest import FakeAgent, auth
from mokli.agent.tools.context import RequestContext
from mokli.agent_api.context import AgentApiServices
from mokli.agent_api.events import session_key_for, tool_data

DECISION = {
    "verdict": "buy",
    "entry": 2350.5,
    "stop": 2340.0,
    "targets": [2365.0, 2380.0],
    "confidence": 0.7,
    "reasons": ["reason.trend_aligned"],
    "gates_passed": ["gate.spread", "gate.rr"],
    "permission_level": "propose",
    "plan_id": None,
}


async def _emit(agent: FakeAgent, services: AgentApiServices, session: str, payload: dict) -> str:
    tool = agent.tools.get("emit_result")
    assert tool is not None, "emit_result must be registered on the agent's registry"
    tool.set_context(RequestContext(session_key=session_key_for(session), channel="agent_api", chat_id=session))
    raw = await tool.execute(type="decision", payload=payload)
    return json.loads(raw)["result_id"]


async def test_emit_result_persists_and_streams(
    client: TestClient, agent: FakeAgent, services: AgentApiServices,
) -> None:
    session = (await (await client.post("/api/v2/sessions", headers=auth())).json())["id"]
    result_id = await _emit(agent, services, session, DECISION)

    resp = await client.get(f"/api/v2/results/{result_id}", headers=auth())
    assert resp.status == 200
    body = await resp.json()
    assert body["type"] == "decision"
    assert body["payload"]["verdict"] == "buy"
    assert body["session"] == session

    listed = await (await client.get(
        f"/api/v2/results?session={session}&type=decision", headers=auth(),
    )).json()
    assert [r["id"] for r in listed["results"]] == [result_id]

    timeline = services.sessions.timeline(session)
    structured = [e for e in timeline if e["kind"] == "structured"]
    assert structured and structured[0]["data"]["result_id"] == result_id


async def test_emit_result_rejects_invalid_payload(
    client: TestClient, agent: FakeAgent, services: AgentApiServices,
) -> None:
    tool = agent.tools.get("emit_result")
    assert tool is not None
    raw = await tool.execute(type="decision", payload={"verdict": "maybe"})
    assert "invalid_result" in str(raw)


async def test_result_html_localised_rtl(
    client: TestClient, agent: FakeAgent, services: AgentApiServices,
) -> None:
    session = (await (await client.post("/api/v2/sessions", headers=auth())).json())["id"]
    result_id = await _emit(agent, services, session, DECISION)
    resp = await client.get(f"/api/v2/results/{result_id}/html?locale=ar", headers=auth())
    assert resp.status == 200
    assert resp.headers["Content-Type"].startswith("text/html")
    html = await resp.text()
    assert 'dir="rtl"' in html
    assert "2350.5" in html or "2,350.5" in html
    missing = await client.get("/api/v2/results/res_missing/html", headers=auth())
    assert missing.status == 404


async def test_labels_catalog(client: TestClient) -> None:
    ar = await (await client.get("/api/v2/labels?locale=ar", headers=auth())).json()
    en = await (await client.get("/api/v2/labels?locale=en", headers=auth())).json()
    assert ar["dir"] == "rtl" and en["dir"] == "ltr"
    assert set(ar["labels"]) >= set(en["labels"])
    assert ar["labels"] != en["labels"]
    fallback = await (await client.get("/api/v2/labels?locale=xx-YY", headers=auth())).json()
    assert fallback["locale"] == "en"
    prefixed = await (await client.get(
        "/api/v2/labels?locale=en&prefix=risk.", headers=auth(),
    )).json()
    assert prefixed["labels"] and all(k.startswith("risk.") for k in prefixed["labels"])


async def test_approvals_flow_waiting_state(client: TestClient, services: AgentApiServices) -> None:
    session = (await (await client.post("/api/v2/sessions", headers=auth())).json())["id"]
    record = services.approvals.open(
        type="generic",
        summary="approval.summary.generic",
        session=session,
        run=None,
        expires_at=None,
        source_id="p1",
    )
    state = await (await client.get(f"/api/v2/sessions/{session}/state", headers=auth())).json()
    assert state["state"] == "waiting"
    assert state["waiting_for"] == {"kind": "approval", "id": record["id"]}
    assert state["pending_approvals"] == [record["id"]]

    pending = await (await client.get("/api/v2/approvals?status=pending", headers=auth())).json()
    assert [a["id"] for a in pending["approvals"]] == [record["id"]]

    bad = await client.post(f"/api/v2/approvals/{record['id']}", json={"decision": "maybe"}, headers=auth())
    assert bad.status == 400

    decided = await client.post(
        f"/api/v2/approvals/{record['id']}", json={"decision": "confirm"}, headers=auth(),
    )
    assert decided.status == 200
    body = await decided.json()
    assert body["status"] == "confirmed"
    assert body["decided_by"] == "bootstrap"

    again = await client.post(
        f"/api/v2/approvals/{record['id']}", json={"decision": "cancel"}, headers=auth(),
    )
    assert again.status == 409

    state = await (await client.get(f"/api/v2/sessions/{session}/state", headers=auth())).json()
    assert state["state"] == "completed"
    timeline = services.sessions.timeline(session)
    assert [e["data"]["status"] for e in timeline if e["kind"] == "approval"] == ["pending", "confirmed"]


async def test_log_merges_gateway_events_and_permission_audit(
    client: TestClient, services: AgentApiServices,
) -> None:
    from mokli.trading.permissions.model import Mt5Permissions
    from mokli.trading.permissions.store import get_permission_store

    session = (await (await client.post("/api/v2/sessions", headers=auth())).json())["id"]
    services.hub.publish(
        session, "tool", tool_data("finished", name="mt5_propose_order", call_id="c1", summary="ok"),
    )
    services.hub.publish(
        session,
        "tool",
        tool_data("failed", name="mt5_confirm_order", call_id="c2", summary="gate spread blocked"),
    )
    services.hub.publish(session, "tool", tool_data("finished", name="analyze_gold", call_id="c3"))
    get_permission_store().save(Mt5Permissions(level="execute", can_open=True), who="test")

    body = await (await client.get("/api/v2/log", headers=auth())).json()
    kinds = {entry["kind"] for entry in body["entries"]}
    assert {"execution", "gate", "permission"} <= kinds
    assert all(entry["data"].get("name") != "analyze_gold" for entry in body["entries"])
    permission = next(e for e in body["entries"] if e["kind"] == "permission")
    assert permission["data"]["to"]["level"] == "execute"

    only = await (await client.get("/api/v2/log?kinds=gate", headers=auth())).json()
    assert [e["kind"] for e in only["entries"]] == ["gate"]
    assert only["entries"][0]["data"]["name"] == "mt5_confirm_order"

    bad = await client.get("/api/v2/log?kinds=nope", headers=auth())
    assert bad.status == 400
