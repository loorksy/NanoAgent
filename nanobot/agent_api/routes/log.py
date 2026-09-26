"""Operator log (``GET /api/v2/log?kinds=&from=&limit=``).

Merges three sources into one time-ordered list of ``{ts, kind, source, data}``:

* ``approval`` / ``execution`` / ``gate`` / ``job`` / ``notification`` from the
  gateway event log (``tool`` events are exposed as ``execution`` when they
  touch an MT5 tool, and as ``gate`` when the tool reported a blocked gate);
* ``decision`` from the append-only trade decision memory (``trades.jsonl``);
* ``permission`` from the MT5 permission audit trail.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from pathlib import Path
from typing import Literal, cast

from aiohttp import web

from nanobot.agent_api.auth import require_scope
from nanobot.agent_api.context import services
from nanobot.agent_api.errors import ApiError
from nanobot.agent_api.events import GatewayEvent, JsonObject
from nanobot.agent_api.routes._util import ok, query_int

LogKind = Literal[
    "decision",
    "execution",
    "gate",
    "approval",
    "permission",
    "job",
    "notification",
    "structured",
]
LOG_KINDS: tuple[LogKind, ...] = (
    "decision",
    "execution",
    "gate",
    "approval",
    "permission",
    "job",
    "notification",
    "structured",
)
_EVENT_KINDS_FOR: dict[LogKind, tuple[str, ...]] = {
    "execution": ("tool",),
    "gate": ("tool",),
    "approval": ("approval",),
    "job": ("job",),
    "notification": ("notification",),
    "structured": ("structured",),
}
_MT5_TOOL_PREFIX = "mt5_"
_GATE_MARKERS = ("gate", "blocked", "LivePlanActive", "policy")
_EPOCH_MS_THRESHOLD = 10**12


def _to_ms(value: object) -> int:
    """Accept epoch seconds or milliseconds and return milliseconds."""
    if not isinstance(value, int) or isinstance(value, bool):
        return 0
    return value * 1000 if value < _EPOCH_MS_THRESHOLD else value


def parse_kinds(raw: str | None) -> tuple[LogKind, ...]:
    if not raw or not raw.strip():
        return LOG_KINDS
    kinds: list[LogKind] = []
    for part in raw.split(","):
        name = part.strip()
        if not name:
            continue
        if name not in LOG_KINDS:
            raise ApiError(400, "invalid_query", details={"param": "kinds", "value": name})
        kinds.append(name)
    return tuple(kinds) or LOG_KINDS


def _entry(ts: int, kind: LogKind, source: str, data: JsonObject, *, id: str = "") -> JsonObject:
    return {"id": id, "ts": ts, "kind": kind, "source": source, "data": data}


def _classify_tool(event: GatewayEvent) -> LogKind | None:
    name = str(event["data"].get("name") or "")
    if not name.startswith(_MT5_TOOL_PREFIX):
        return None
    summary = str(event["data"].get("summary") or "")
    if event["data"].get("event") == "failed" or any(m in summary for m in _GATE_MARKERS):
        return "gate"
    return "execution"


def _from_events(events: list[GatewayEvent], kinds: tuple[LogKind, ...]) -> list[JsonObject]:
    out: list[JsonObject] = []
    wanted = set(kinds)
    for event in events:
        data: JsonObject = {**event["data"], "session": event["session"], "run": event["run"]}
        if event["kind"] == "tool":
            kind = _classify_tool(event)
            if kind is None or kind not in wanted:
                continue
            out.append(_entry(event["ts"], kind, "gateway", data, id=event["id"]))
            continue
        kind_map: dict[str, LogKind] = {
            "approval": "approval",
            "job": "job",
            "notification": "notification",
            "structured": "structured",
        }
        kind = kind_map.get(event["kind"])
        if kind is None or kind not in wanted:
            continue
        out.append(_entry(event["ts"], kind, "gateway", data, id=event["id"]))
    return out


def _decisions(limit: int) -> list[JsonObject]:
    try:
        from nanobot.trading.memory.decisions import list_recent_decisions
    except Exception:
        return []
    rows = cast(list[dict[str, object]], list_recent_decisions(limit))
    out: list[JsonObject] = []
    for row in rows:
        out.append(
            _entry(
                _to_ms(row.get("ts")),
                "decision",
                "trades.jsonl",
                dict(row),
                id=str(row.get("id") or ""),
            ),
        )
    return out


def _permission_audit(limit: int) -> list[JsonObject]:
    try:
        from nanobot.trading.permissions.store import get_permission_store
    except Exception:
        return []
    entries = cast(list[dict[str, object]], get_permission_store().audit(limit=limit))
    out: list[JsonObject] = []
    for entry in entries:
        out.append(_entry(_to_ms(entry.get("ts")), "permission", "mt5_permissions", dict(entry)))
    return out


async def get_log(request: web.Request) -> web.Response:
    require_scope(request, "read")
    svc = services(request)
    kinds = parse_kinds(request.query.get("kinds"))
    limit = query_int(request, "limit", 200, maximum=2000)
    since_raw = request.query.get("from")
    since: int | None = None
    if since_raw:
        try:
            since = int(since_raw)
        except ValueError as exc:
            raise ApiError(400, "invalid_query", details={"param": "from"}) from exc
    session = request.query.get("session") or None

    event_kinds: set[str] = set()
    for kind in kinds:
        event_kinds.update(_EVENT_KINDS_FOR.get(kind, ()))
    entries: list[JsonObject] = []
    if event_kinds:
        events = svc.event_log.query(
            kinds=tuple(sorted(event_kinds)),
            since_ts=since,
            session=session,
            limit=limit,
        )
        entries.extend(_from_events(events, kinds))
    loaders: list[Callable[[int], list[JsonObject]]] = []
    if "decision" in kinds:
        loaders.append(_decisions)
    if "permission" in kinds:
        loaders.append(_permission_audit)
    for loader in loaders:
        rows = await asyncio.to_thread(loader, limit)
        if since is not None:
            rows = [row for row in rows if cast(int, row["ts"]) >= since]
        entries.extend(rows)

    entries.sort(key=lambda row: (cast(int, row["ts"]), str(row["id"])), reverse=True)
    return ok({"entries": entries[:limit], "kinds": list(kinds), "count": min(len(entries), limit)})


def _journal_path() -> Path:
    from nanobot.config.paths import get_data_dir

    return get_data_dir() / "memory" / "journal.jsonl"


async def get_journal(request: web.Request) -> web.Response:
    require_scope(request, "read")
    path = _journal_path()
    entries: list[JsonObject] = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            parsed: object = json.loads(line)
            if isinstance(parsed, dict):
                entries.append(cast(JsonObject, parsed))
    return ok({"entries": entries[-50:]})


async def get_calendar(request: web.Request) -> web.Response:
    require_scope(request, "read")
    from nanobot.trading.intel.calendar_view import rows_from_events

    def _load() -> list[dict[str, str]]:
        try:
            from nanobot.trading.news.forex_factory import fetch_upcoming_events

            return rows_from_events(list(fetch_upcoming_events()))
        except Exception:
            return []

    rows = await asyncio.to_thread(_load)
    return ok({"events": rows})


def register(router: web.UrlDispatcher, prefix: str) -> None:
    router.add_get(f"{prefix}/log/journal", get_journal)
    router.add_get(f"{prefix}/log/calendar", get_calendar)
    router.add_get(f"{prefix}/log", get_log)
