"""Jobs REST (``/api/v2/jobs``): cron + goals."""

from __future__ import annotations

from aiohttp import web

from nanobot.agent_api.auth import require_scope
from nanobot.agent_api.context import services
from nanobot.agent_api.errors import ApiError
from nanobot.agent_api.events import job_data, session_key_for
from nanobot.agent_api.routes._util import json_body, ok, optional_str


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


def register(router: web.UrlDispatcher, prefix: str) -> None:
    router.add_get(f"{prefix}/jobs", list_jobs)
    router.add_post(f"{prefix}/jobs", create_job)
    router.add_get(f"{prefix}/jobs/{{id}}", get_job)
    router.add_post(f"{prefix}/jobs/{{id}}/pause", pause_job)
    router.add_post(f"{prefix}/jobs/{{id}}/resume", resume_job)
    router.add_post(f"{prefix}/jobs/{{id}}/cancel", cancel_job)
    router.add_delete(f"{prefix}/jobs/{{id}}", cancel_job)
