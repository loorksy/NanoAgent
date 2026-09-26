"""Approvals REST (``/api/v2/approvals``)."""

from __future__ import annotations

from aiohttp import web

from mokli.agent_api.approvals import ApprovalStatus
from mokli.agent_api.auth import require_scope
from mokli.agent_api.context import services
from mokli.agent_api.errors import ApiError
from mokli.agent_api.routes._util import json_body, ok, query_int, require_str

_STATUSES = ("pending", "confirmed", "cancelled", "expired", "failed")


async def list_approvals(request: web.Request) -> web.Response:
    require_scope(request, "read")
    svc = services(request)
    svc.approvals.expire_due()
    svc.approvals.sync_proposals()
    status_raw = request.query.get("status")
    status: ApprovalStatus | None = None
    if status_raw:
        if status_raw not in _STATUSES:
            raise ApiError(400, "invalid_query", details={"param": "status"})
        status = status_raw
    limit = query_int(request, "limit", 100, maximum=500)
    return ok({"approvals": svc.approvals.list(status=status, limit=limit)})


async def get_approval(request: web.Request) -> web.Response:
    require_scope(request, "read")
    record = services(request).approvals.get(request.match_info["id"])
    if record is None:
        raise ApiError(404, "approval_not_found")
    return ok(record)


async def decide(request: web.Request) -> web.Response:
    principal = require_scope(request, "approve")
    svc = services(request)
    body = await json_body(request)
    decision = require_str(body, "decision")
    if decision not in ("confirm", "cancel"):
        raise ApiError(400, "invalid_field", details={"field": "decision"})
    record = await svc.approvals.decide(request.match_info["id"], decision)
    return ok({**record, "decided_by": principal["client_id"]})


def register(router: web.UrlDispatcher, prefix: str) -> None:
    router.add_get(f"{prefix}/approvals", list_approvals)
    router.add_get(f"{prefix}/approvals/{{id}}", get_approval)
    router.add_post(f"{prefix}/approvals/{{id}}", decide)
