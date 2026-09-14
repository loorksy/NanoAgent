"""HTTP handlers for /api/trading/* routes."""

from __future__ import annotations

import asyncio
import concurrent.futures
from dataclasses import replace
from typing import Any, TypeVar

from websockets.http11 import Request as WsRequest
from websockets.http11 import Response

from nanobot.agent.tools.context import RequestContext, current_request_context, request_context
from nanobot.providers.factory import load_provider_snapshot
from nanobot.trading.config import load_trading_config
from nanobot.trading.gold import DATA_SYMBOL, GoldOnlyError, coerce_to_gold
from nanobot.trading.oanda import candle_to_wire, fetch_candles, fetch_quote
from nanobot.trading.crew.debate import run_debate_crew
from nanobot.trading.orchestrator import run_unified_chart_agent
from nanobot.trading.stage_delivery import TradingStagePublisher
from nanobot.trading.teams.runtime import run_swarm
from nanobot.trading.teams.subagent_runner import create_trading_subagent_manager
from nanobot.trading.paper import record_paper_action
from nanobot.trading.chart_capture import ChartCaptureError, submit_chart_capture, validate_chart_frames
from nanobot.trading.chart_host_bridge import get_chart_host_bridge
from nanobot.trading.chart_host_token import verify_chart_host_page_token
from nanobot.webui.http_utils import bearer_token as _bearer_token
from nanobot.trading.recommendations.followup import (
    CLOSED_OUTCOME_STATUSES,
    LIVE_OUTCOME_STATUSES,
    refresh_recommendation_outcomes,
)
from nanobot.trading.recommendations.store import list_recommendations
from nanobot.trading.result_wire import result_to_wire
from nanobot.trading.runtime_state import get_runtime_store
from nanobot.utils.llm_runtime import runtime_from_provider_snapshot
from nanobot.webui.http_utils import http_error as _http_error
from nanobot.webui.http_utils import http_json_response as _http_json_response
from nanobot.webui.http_utils import parse_query as _parse_query
from nanobot.webui.http_utils import query_first as _query_first

_T = TypeVar("_T")


def _run_async(coro: Any) -> _T:
    """Run a coroutine from sync HTTP handlers (works inside a running event loop)."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


def _parse_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def handle_trading_klines(request: WsRequest) -> Response:
    params = _parse_query(request.path)
    symbol = coerce_to_gold(_query_first(params, "symbol"))
    interval = (_query_first(params, "interval") or "1h").strip()
    limit = _parse_int(_query_first(params, "limit")) or 300
    before_ms = _parse_int(_query_first(params, "before"))
    from_ms = _parse_int(_query_first(params, "from"))
    to_ms = _parse_int(_query_first(params, "to"))

    config = load_trading_config()
    if not config.oanda_configured:
        return _http_json_response({
            "symbol": symbol,
            "interval": interval,
            "source": "oanda",
            "candles": [],
            "pending": False,
            "error": "Market data unavailable — OANDA is not configured.",
        })

    try:
        candles, has_more = fetch_candles(
            symbol,
            interval,
            limit,
            before_ms=before_ms,
            from_ms=from_ms,
            to_ms=to_ms,
            config=config,
        )
    except GoldOnlyError as exc:
        return _http_error(400, str(exc))
    except Exception as exc:
        return _http_json_response({
            "symbol": symbol,
            "interval": interval,
            "source": "oanda",
            "candles": [],
            "pending": False,
            "error": f"Failed to fetch candles: {exc}",
        }, status=502)

    return _http_json_response({
        "symbol": symbol,
        "interval": interval,
        "source": "oanda",
        "candles": [candle_to_wire(c) for c in candles],
        "hasMore": has_more,
        "pending": len(candles) == 0,
    })


def handle_trading_quote(request: WsRequest) -> Response:
    params = _parse_query(request.path)
    symbol = coerce_to_gold(_query_first(params, "symbol"))

    config = load_trading_config()
    if not config.oanda_configured:
        return _http_json_response({
            "symbol": symbol,
            "configured": False,
            "quote": None,
            "error": "Market data unavailable — OANDA is not configured.",
        })

    try:
        quote = fetch_quote(symbol, config=config)
    except GoldOnlyError as exc:
        return _http_error(400, str(exc))
    except Exception as exc:
        return _http_json_response({
            "symbol": symbol,
            "configured": True,
            "quote": None,
            "error": f"Failed to fetch quote: {exc}",
        }, status=502)

    if quote is None:
        return _http_json_response({
            "symbol": symbol,
            "configured": True,
            "quote": None,
            "error": "No quote returned — check OANDA_ACCOUNT_ID.",
        })

    return _http_json_response({
        "symbol": quote.symbol,
        "configured": True,
        "quote": {
            "bid": quote.bid,
            "ask": quote.ask,
            "mid": quote.mid,
            "tradeable": quote.tradeable,
        },
    })


def handle_trading_status(_request: WsRequest) -> Response:
    config = load_trading_config()
    state = get_runtime_store().snapshot()
    return _http_json_response({
        "symbol": DATA_SYMBOL,
        "oanda_configured": config.oanda_configured,
        "oanda_env": config.oanda_env,
        "runtime": state.to_dict(),
    })


def handle_trading_runtime_update(request: WsRequest) -> Response:
    params = _parse_query(request.path)
    changes: dict[str, bool] = {}
    for key in ("paused", "kill_switch", "paper_mode"):
        raw = _query_first(params, key)
        if raw is None:
            continue
        changes[key] = raw.strip().lower() in {"1", "true", "yes", "on"}
    if not changes:
        return _http_error(400, "No runtime fields provided")
    state = get_runtime_store().update(**changes)
    return _http_json_response({"runtime": state.to_dict()})


def analyze_request_context() -> RequestContext:
    """Request context with the configured default LLM runtime (same as chat).

    HTTP analyze runs outside AgentLoop, so Lonora's synthesizer otherwise
    sees no provider and returns WAIT / "no usable decision".
    """
    existing = current_request_context()
    runtime = existing.runtime if existing is not None else None
    if runtime is None:
        try:
            runtime = runtime_from_provider_snapshot(load_provider_snapshot())
        except ValueError:
            runtime = None
    if existing is not None:
        return existing if existing.runtime is runtime else replace(existing, runtime=runtime)
    return RequestContext(
        channel="webui",
        chat_id="trading-analyze",
        runtime=runtime,
    )


async def _run_trading_analyze(
    interval: str,
    team_mode: str,
    preset: str | None,
) -> Any:
    """Run analyze inside a bound default-LLM context (thread-pool safe)."""
    with request_context(analyze_request_context()):
        from nanobot.trading.chart_capture import resolve_visual_capture

        manager = create_trading_subagent_manager()
        publisher = TradingStagePublisher(None, channel="webui", chat_id="trading-analyze")
        visual_capture = resolve_visual_capture(publisher)
        if team_mode == "debate":
            debate = await run_debate_crew(
                subagent_manager=manager,
                publisher=publisher,
                interval=interval,
                visual_capture=visual_capture,
            )
            return debate.final
        if team_mode == "swarm":
            swarm = await run_swarm(
                preset or "gold_analysis_committee",
                subagent_manager=manager,
                publisher=publisher,
                interval=interval,
                visual_capture=visual_capture,
            )
            return swarm["final"]
        return await run_unified_chart_agent(
            interval=interval,
            team_mode="core",
            visual_capture=visual_capture,
        )


def handle_trading_analyze(request: WsRequest) -> Response:
    params = _parse_query(request.path)
    interval = (_query_first(params, "interval") or "15m").strip()
    team_mode = (_query_first(params, "team_mode") or "core").strip()
    preset = _query_first(params, "preset")
    if team_mode not in {"", "core", "debate", "swarm"}:
        return _http_error(400, "team_mode must be core, debate, or swarm")

    try:
        result = _run_async(_run_trading_analyze(interval, team_mode, preset))
        if result is None:
            return _http_error(500, "Analysis produced no result")
        return _http_json_response(result_to_wire(result))
    except Exception as exc:
        return _http_error(500, f"Analysis failed: {exc}")


def _enrich_recommendation_rows(rows: list[dict]) -> list[dict]:
    from nanobot.trading.paper import paper_actions_index

    paper = paper_actions_index()
    enriched: list[dict] = []
    for row in rows:
        rec_id = str(row.get("id") or "")
        enriched.append(
            {
                **row,
                "paperAction": paper.get(rec_id),
            }
        )
    return enriched


def handle_trading_recommendations(_request: WsRequest) -> Response:
    from nanobot.trading.gold import DATA_SYMBOL
    from nanobot.trading.oanda import fetch_quote
    from nanobot.trading.recommendations.outcome_delivery import outcome_web_alerts_from_transitions

    live_price = None
    try:
        quote = fetch_quote(DATA_SYMBOL)
        live_price = quote.mid if quote else None
    except Exception:
        live_price = None
    _, transitions = refresh_recommendation_outcomes(live_price=live_price)
    rows = _enrich_recommendation_rows(list_recommendations(limit=100))
    return _http_json_response({
        "recommendations": rows,
        "recentOutcomeAlerts": outcome_web_alerts_from_transitions(
            transitions,
            live_price=live_price,
        ),
    })


def handle_trading_performance(_request: WsRequest) -> Response:
    from nanobot.config.paths import get_data_dir
    from nanobot.trading.memory.decisions import list_recent_decisions
    from nanobot.trading.gold import DATA_SYMBOL
    from nanobot.trading.oanda import fetch_quote
    from nanobot.trading.recommendations.outcome_delivery import outcome_web_alerts_from_transitions

    live_price = None
    try:
        quote = fetch_quote(DATA_SYMBOL)
        live_price = quote.mid if quote else None
    except Exception:
        live_price = None
    _, transitions = refresh_recommendation_outcomes(live_price=live_price)
    recs = list_recommendations(limit=200)
    decisions = list_recent_decisions(limit=20)
    open_count = sum(1 for row in recs if row.get("status") in LIVE_OUTCOME_STATUSES)
    closed_count = sum(1 for row in recs if row.get("status") in CLOSED_OUTCOME_STATUSES)
    directions = {"buy": 0, "sell": 0, "wait": 0}
    outcomes = {
        "valid_now": 0,
        "awaiting_activation": 0,
        "waiting": 0,
        "in_trade": 0,
        "tp1": 0,
        "invalidated": 0,
        "expired": 0,
        "blocked": 0,
    }
    for row in recs:
        direction = str(row.get("direction", "wait")).lower()
        if direction in directions:
            directions[direction] += 1
        status = str(row.get("status") or "valid_now")
        if status in outcomes:
            outcomes[status] += 1
    paper_path = get_data_dir() / "trading" / "paper_ledger.jsonl"
    paper_actions = 0
    if paper_path.exists():
        paper_actions = sum(1 for line in paper_path.read_text(encoding="utf-8").splitlines() if line.strip())
    return _http_json_response({
        "totalRecommendations": len(recs),
        "openRecommendations": open_count,
        "closedRecommendations": closed_count,
        "directionBreakdown": directions,
        "outcomeBreakdown": outcomes,
        "paperActions": paper_actions,
        "recentRecommendations": _enrich_recommendation_rows(recs[:10]),
        "recentDecisions": decisions,
        "recentOutcomeAlerts": outcome_web_alerts_from_transitions(
            transitions,
            live_price=live_price,
        ),
    })


def _chart_host_authorized(request: WsRequest) -> bool:
    token = _bearer_token(request.headers)
    return bool(token and verify_chart_host_page_token(token))


def handle_trading_chart_host_poll(request: WsRequest) -> Response:
    if not _chart_host_authorized(request):
        return _http_error(401, "unauthorized")
    job = get_chart_host_bridge().poll_job()
    return _http_json_response({"job": job})


def handle_trading_chart_host_submit(request: WsRequest) -> Response:
    if not _chart_host_authorized(request):
        return _http_error(401, "unauthorized")
    payload = getattr(request, "_nanobot_webui_mutation_payload", None)
    if not isinstance(payload, dict):
        return _http_error(400, "invalid body")
    capture_id = str(payload.get("captureId") or payload.get("capture_id") or "")
    frames = payload.get("frames")
    if not capture_id:
        return _http_error(400, "captureId required")
    if not isinstance(frames, list):
        return _http_error(400, "frames must be a list")
    try:
        validate_chart_frames(frames)
    except ChartCaptureError as exc:
        return _http_error(400, str(exc))
    if not get_chart_host_bridge().submit(capture_id, {"frames": frames}):
        return _http_error(404, "No pending chart-host capture for that id")
    return _http_json_response({"ok": True})


def handle_trading_chart_capture(_request: WsRequest) -> Response:
    payload = getattr(_request, "_nanobot_webui_mutation_payload", None)
    if isinstance(payload, dict):
        capture_id = str(payload.get("captureId") or payload.get("capture_id") or "")
        frames = payload.get("frames")
    else:
        params = _parse_query(_request.path)
        capture_id = _query_first(params, "capture_id") or ""
        frames = None
    if not capture_id:
        return _http_error(400, "captureId required")
    if frames is None:
        return _http_error(400, "frames required")
    if not isinstance(frames, list):
        return _http_error(400, "frames must be a list")
    session_key = ""
    if isinstance(payload, dict):
        session_key = str(payload.get("sessionKey") or payload.get("session_key") or "")
    try:
        validate_chart_frames(frames)
    except ChartCaptureError as exc:
        return _http_error(400, str(exc))
    if not submit_chart_capture(
        capture_id,
        {"frames": frames},
        session_key=session_key or None,
    ):
        return _http_error(404, "No pending chart capture for that id or session mismatch")
    return _http_json_response({"ok": True})


def handle_trading_briefing(_request: WsRequest) -> Response:
    from nanobot.trading.config import load_trading_config
    from nanobot.trading.oanda import fetch_quote
    from nanobot.trading.recommendations.followup import (
        grade_outcome_status,
        latest_open_recommendation,
        refresh_recommendation_outcomes,
    )

    config = load_trading_config()
    quote = fetch_quote("XAUUSD", config=config) if config.oanda_configured else None
    live_price = quote.mid if quote else None
    refresh_recommendation_outcomes(live_price=live_price)
    latest = latest_open_recommendation()
    if latest:
        latest = {
            **latest,
            "outcomeStatus": grade_outcome_status(latest, live_price=live_price),
            "livePrice": live_price,
        }
    recs = list_recommendations(limit=5)
    return _http_json_response({
        "symbol": "XAUUSD",
        "quote": {
            "mid": quote.mid if quote else None,
            "bid": quote.bid if quote else None,
            "ask": quote.ask if quote else None,
        },
        "openRecommendation": latest,
        "recentRecommendations": recs,
        "summary": (
            f"Gold {quote.mid:.2f}" if quote and quote.mid is not None
            else "Gold — quote unavailable"
        ),
    })


def handle_trading_paper(request: WsRequest) -> Response:
    params = _parse_query(request.path)
    rec_id = _query_first(params, "recommendation_id") or ""
    action = _query_first(params, "action") or "approve"
    if not rec_id:
        return _http_error(400, "recommendation_id required")
    entry = record_paper_action(rec_id, action)
    return _http_json_response({"ok": True, "entry": entry})


def dispatch_trading_route(request: WsRequest, path: str) -> Response | None:
    if path == "/api/trading/klines":
        return handle_trading_klines(request)
    if path == "/api/trading/quote":
        return handle_trading_quote(request)
    if path == "/api/trading/status":
        return handle_trading_status(request)
    if path == "/api/trading/runtime/update":
        return handle_trading_runtime_update(request)
    if path == "/api/trading/analyze":
        return handle_trading_analyze(request)
    if path == "/api/trading/recommendations":
        return handle_trading_recommendations(request)
    if path == "/api/trading/briefing":
        return handle_trading_briefing(request)
    if path == "/api/trading/performance":
        return handle_trading_performance(request)
    if path == "/api/trading/paper":
        return handle_trading_paper(request)
    if path == "/api/trading/chart-capture":
        return handle_trading_chart_capture(request)
    if path == "/api/trading/chart-host/poll":
        return handle_trading_chart_host_poll(request)
    if path == "/api/trading/chart-host/submit":
        return handle_trading_chart_host_submit(request)
    return None
