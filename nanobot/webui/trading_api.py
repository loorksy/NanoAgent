"""HTTP handlers for /api/trading/* routes."""

from __future__ import annotations

import asyncio
import concurrent.futures
from typing import Any, TypeVar

from websockets.http11 import Request as WsRequest
from websockets.http11 import Response

from nanobot.trading.config import load_trading_config
from nanobot.trading.crew.debate import run_debate_crew
from nanobot.trading.gold import DATA_SYMBOL, GoldOnlyError, coerce_to_gold
from nanobot.trading.oanda import candle_to_wire, fetch_candles, fetch_quote
from nanobot.trading.orchestrator import run_unified_chart_agent
from nanobot.trading.paper import record_paper_action
from nanobot.trading.recommendations.store import list_recommendations
from nanobot.trading.result_wire import result_to_wire
from nanobot.trading.runtime_state import get_runtime_store
from nanobot.trading.teams.runtime import run_swarm
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


def handle_trading_analyze(request: WsRequest) -> Response:
    params = _parse_query(request.path)
    interval = (_query_first(params, "interval") or "15m").strip()
    team_mode = (_query_first(params, "team_mode") or "core").strip()
    preset = _query_first(params, "preset")

    try:
        if team_mode == "debate":
            debate = _run_async(run_debate_crew())
            result = debate.final
        elif team_mode == "swarm" and preset:
            swarm = _run_async(run_swarm(preset))
            result = swarm["final"]
        else:
            result = _run_async(
                run_unified_chart_agent(interval=interval, team_mode=team_mode)
            )
        if result is None:
            return _http_error(500, "Analysis produced no result")
        return _http_json_response(result_to_wire(result))
    except Exception as exc:
        return _http_error(500, f"Analysis failed: {exc}")


def handle_trading_recommendations(_request: WsRequest) -> Response:
    return _http_json_response({"recommendations": list_recommendations()})


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
    if path == "/api/trading/paper":
        return handle_trading_paper(request)
    return None
