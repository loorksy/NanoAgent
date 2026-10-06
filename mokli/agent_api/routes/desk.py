"""Desk rules and swarm stop (``/api/v2/desk``)."""

from __future__ import annotations

from aiohttp import web
from pydantic import ValidationError

from mokli.agent_api.auth import require_scope
from mokli.agent_api.errors import ApiError
from mokli.agent_api.routes._util import json_body, ok
from mokli.trading.desk.board import request_swarm_stop
from mokli.trading.desk.rules import RULE_KEYS, get_rule_store, grant_action, rules_from_payload


async def get_rules(request: web.Request) -> web.Response:
    require_scope(request, "read")
    rules = get_rule_store().load()
    return ok(rules.model_dump(mode="json"))


async def put_rules(request: web.Request) -> web.Response:
    require_scope(request, "control")
    body = await json_body(request)
    unknown = sorted(key for key in body if key not in RULE_KEYS and key != "updated_by")
    if unknown:
        raise ApiError(400, "invalid_field", details={"field": unknown[0]})
    try:
        rules = rules_from_payload(body, who="operator")
    except (ValueError, ValidationError) as exc:
        raise ApiError(400, "invalid_field", details={"message": str(exc)}) from exc
    stored = get_rule_store().save(rules, who="operator")
    return ok(stored.model_dump(mode="json"))


async def stop_swarm(request: web.Request) -> web.Response:
    require_scope(request, "control")
    return ok({"stopped": request_swarm_stop()})


async def grant_rule(request: web.Request) -> web.Response:
    require_scope(request, "approve")
    action = request.match_info["action"]
    try:
        grant_action(action)
    except KeyError as exc:
        raise ApiError(400, "invalid_field", details={"field": "action"}) from exc
    return ok({"granted": action})


def register(router: web.UrlDispatcher, prefix: str) -> None:
    router.add_get(f"{prefix}/desk/rules", get_rules)
    router.add_put(f"{prefix}/desk/rules", put_rules)
    router.add_post(f"{prefix}/desk/stop", stop_swarm)
    router.add_post(f"{prefix}/desk/rules/{{action}}/grant", grant_rule)
