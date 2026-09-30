"""Jobs REST (``/api/v2/jobs``): cron + goals."""

from __future__ import annotations

import asyncio

from aiohttp import web

from mokli.agent_api.auth import require_scope
from mokli.agent_api.context import services
from mokli.agent_api.errors import ApiError
from mokli.agent_api.events import job_data, session_key_for
from mokli.agent_api.routes._util import json_body, ok, optional_str


async def list_jobs(request: web.Request) -> web.Response:
    require_scope(request, "read")
    return ok({"jobs": services(request).jobs.list()})


async def get_job(request: web.Request) -> web.Response:
    require_scope(request, "read")
    record = services(request).jobs.get(request.match_info["id"])
    if record is None:
        raise ApiError(404, "job_not_found")
    return ok(record)


async def create_job(request: web.Request) -> web.Response:
    require_scope(request, "control")
    svc = services(request)
    body = await json_body(request)
    session = optional_str(body, "session")
    record = svc.jobs.create(body, session_key=session_key_for(session) if session else None)
    _announce(request, record["job_id"], record["status"], record["next_run_at"], session)
    return ok(record, status=201)


async def pause_job(request: web.Request) -> web.Response:
    require_scope(request, "control")
    record = services(request).jobs.pause(request.match_info["id"])
    _announce(request, record["job_id"], record["status"], record["next_run_at"], None)
    return ok(record)


async def resume_job(request: web.Request) -> web.Response:
    require_scope(request, "control")
    record = services(request).jobs.resume(request.match_info["id"])
    _announce(request, record["job_id"], record["status"], record["next_run_at"], None)
    return ok(record)


async def cancel_job(request: web.Request) -> web.Response:
    require_scope(request, "control")
    result = services(request).jobs.cancel(request.match_info["id"])
    if result == "protected":
        raise ApiError(403, "job_protected")
    _announce(request, request.match_info["id"], "cancelled", None, None)
    return ok({"job_id": request.match_info["id"], "status": "cancelled"})


def _announce(
    request: web.Request,
    job_id: str,
    status: str,
    next_run_at: int | None,
    session: str | None,
) -> None:
    svc = services(request)
    if session is None:
        return
    svc.hub.publish(
        session,
        "job",
        job_data(job_id, kind="cron", status=status, next_run_at=next_run_at),
    )


async def task_lab(request: web.Request) -> web.Response:
    """Replay a named strategy. Empty input loads market bars, not a pasted list."""
    require_scope(request, "read")
    from mokli.agent.tools.fast_backtest import candles_from_json
    from mokli.trading.strategy_lab import lab_replay

    body = await json_body(request)
    name = optional_str(body, "name") or "atr_breakout"
    raw = body.get("candles_json")
    candles = candles_from_json(raw if isinstance(raw, str) else "")
    proposal = await asyncio.to_thread(lab_replay, name, candles)
    return ok(proposal)


async def task_desk(request: web.Request) -> web.Response:
    """Approvals inbox companion: circuits and the weekend plan (R5, R7, R15)."""
    require_scope(request, "read")
    from datetime import UTC, datetime

    from mokli.trading.bots.circuit import get_circuit
    from mokli.trading.closed_market import closed_market_plan

    plan = closed_market_plan(now=datetime.now(tz=UTC), last_close=0.0, friday_close=0.0, atr=0.0)
    return ok({"circuits": get_circuit().snapshot(), "closed_market": plan})


def register(router: web.UrlDispatcher, prefix: str) -> None:
    # ``tasks`` is the Mokli path from design 04 §3.2. Same handlers as jobs.
    router.add_get(f"{prefix}/tasks/desk", task_desk)
    router.add_post(f"{prefix}/tasks/lab", task_lab)
    for collection in ("jobs", "tasks"):
        router.add_get(f"{prefix}/{collection}", list_jobs)
        router.add_post(f"{prefix}/{collection}", create_job)
        router.add_get(f"{prefix}/{collection}/{{id}}", get_job)
        router.add_post(f"{prefix}/{collection}/{{id}}/pause", pause_job)
        router.add_post(f"{prefix}/{collection}/{{id}}/resume", resume_job)
        router.add_post(f"{prefix}/{collection}/{{id}}/cancel", cancel_job)
        router.add_delete(f"{prefix}/{collection}/{{id}}", cancel_job)
