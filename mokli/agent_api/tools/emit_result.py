"""``emit_result``: the single tool the agent uses to publish structured results.

The tool is registered explicitly by the gateway (``register_emit_result_tool``)
because it needs the live :class:`ResultsStore` / :class:`EventHub` instances;
``ToolLoader`` does not scan this package.
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, cast

from mokli.agent.tools.base import Tool
from mokli.agent.tools.context import RequestContext
from mokli.agent.tools.registry import ToolRegistry
from mokli.agent_api.errors import ApiError
from mokli.agent_api.events import JsonObject, session_id_for_key, structured_data
from mokli.agent_api.hub import EventHub
from mokli.agent_api.results import RESULT_TYPES, ResultsStore

_PARAMETERS: dict[str, Any] = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": list(RESULT_TYPES),
            "description": "Structured result type (market, analysis, scenarios, risk, decision, approval, plan_status, scorecard).",
        },
        "payload": {
            "type": "object",
            "description": "Result payload matching mokli/agent_api/schemas/<type>.json. Use reason/label keys, never prose.",
        },
    },
    "required": ["type", "payload"],
}


class EmitResultTool(Tool):
    """Validate a payload against its schema, persist it, and stream a ``structured`` event."""

    _plugin_discoverable = False
    _scopes = {"core", "subagent"}

    def __init__(self, store: ResultsStore, hub: EventHub) -> None:
        self._store = store
        self._hub = hub
        self._ctx: RequestContext | None = None

    @property
    def name(self) -> str:
        return "emit_result"

    @property
    def parameters(self) -> dict[str, Any]:
        return deepcopy(_PARAMETERS)

    @property
    def description(self) -> str:
        return (
            "Publish a structured trading result card to the client instead of formatting it "
            "as text. Types: market, analysis, scenarios, risk, decision, approval, plan_status, "
            "scorecard. The payload must match the schema for that type; use reason keys."
        )

    def set_context(self, ctx: RequestContext) -> None:
        self._ctx = ctx

    async def execute(self, **kwargs: Any) -> Any:
        result_type = kwargs.get("type")
        payload = kwargs.get("payload")
        if not isinstance(result_type, str) or not isinstance(payload, dict):
            return self.error("emit_result requires 'type' (string) and 'payload' (object)")
        session_key = self._ctx.session_key if self._ctx is not None else None
        session = session_id_for_key(session_key) if session_key else None
        run = self._hub.state.active_run(session) if session else None
        try:
            record = self._store.put(
                result_type, cast(JsonObject, payload), session=session, run=run,
            )
        except ApiError as exc:
            return self.error(json.dumps(exc.envelope(), ensure_ascii=False))
        if session is not None:
            self._hub.publish(
                session,
                "structured",
                structured_data(record["type"], record["id"], record["payload"]),
                run=run,
            )
        return json.dumps({"result_id": record["id"], "type": record["type"]})


def register_emit_result_tool(
    registry: ToolRegistry, store: ResultsStore, hub: EventHub,
) -> EmitResultTool:
    tool = EmitResultTool(store, hub)
    registry.register(tool)
    return tool
