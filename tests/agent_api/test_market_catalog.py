"""Chart candles and the operator skill/tool catalog."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from aiohttp.test_utils import TestClient

from agent_api.conftest import auth


async def test_klines_returns_wire_candles(client: TestClient, monkeypatch) -> None:
    candle = SimpleNamespace(
        time_ms=1_700_000_000_000,
        open=2300.0,
        high=2310.0,
        low=2290.0,
        close=2305.0,
        volume=12,
        complete=True,
    )

    def fake_fetch(*_args, **_kwargs):
        return [candle], False

    monkeypatch.setattr("mokli.trading.oanda.fetch_candles", fake_fetch)
    monkeypatch.setattr(
        "mokli.trading.config.load_trading_config",
        lambda: SimpleNamespace(oanda_configured=True),
    )
    response = await client.get(
        "/api/v2/market/klines?interval=15m&limit=10&from=1&to=2",
        headers=auth(),
    )
    assert response.status == 200
    body = await response.json()
    assert body["configured"] is True
    assert body["candles"][0]["time"] == 1_700_000_000
    assert body["candles"][0]["close"] == 2305.0


async def test_klines_stay_on_oanda_and_symbols_are_gold(
    client: TestClient, monkeypatch
) -> None:
    candle = SimpleNamespace(
        time_ms=1_700_000_000_000,
        open=2300.0,
        high=2310.0,
        low=2290.0,
        close=2305.0,
        volume=4,
        complete=True,
    )
    monkeypatch.setattr(
        "mokli.trading.config.load_trading_config",
        lambda: SimpleNamespace(oanda_configured=True, metaapi_configured=False),
    )
    monkeypatch.setattr(
        "mokli.trading.oanda.fetch_candles",
        lambda *_args, **_kwargs: ([candle], False),
    )
    candles = await client.get(
        "/api/v2/market/klines?symbol=XAUUSD&interval=15m&limit=10",
        headers=auth(),
    )
    assert candles.status == 200
    body = await candles.json()
    assert body["source"] == "oanda"
    assert body["symbol"] == "XAUUSD"
    assert body["candles"][0]["close"] == 2305.0

    symbols = await client.get("/api/v2/market/symbols?q=xau", headers=auth())
    assert symbols.status == 200
    listed = await symbols.json()
    assert listed["source"] == "oanda"
    assert listed["symbols"][0]["name"] == "XAUUSD"

    other = await client.get("/api/v2/market/symbols?q=eur", headers=auth())
    assert (await other.json())["symbols"] == []


async def test_quote_uses_metaapi_when_configured(client: TestClient, monkeypatch) -> None:
    from mokli.trading.oanda import OandaQuote

    monkeypatch.setattr(
        "mokli.trading.config.load_trading_config",
        lambda: SimpleNamespace(oanda_configured=False, metaapi_configured=True),
    )
    monkeypatch.setattr(
        "mokli.trading.market_context.fetch_metaapi_quote",
        lambda *_args, **_kwargs: OandaQuote(
            symbol="XAUUSD",
            bid=2400.1,
            ask=2400.3,
            mid=2400.2,
            tradeable=True,
            quoted_at="2026-09-29T12:00:00Z",
        ),
    )

    def _oanda_must_not_run(*_args, **_kwargs):
        raise AssertionError("oanda quote")

    monkeypatch.setattr("mokli.trading.oanda.fetch_quote", _oanda_must_not_run)
    quote = await client.get("/api/v2/market/quote?symbol=XAUUSD", headers=auth())
    assert quote.status == 200
    quoted = await quote.json()
    assert quoted["source"] == "metaapi"
    assert quoted["quote"]["bid"] == 2400.1


async def test_klines_unconfigured_feed(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        "mokli.trading.config.load_trading_config",
        lambda: SimpleNamespace(oanda_configured=False),
    )
    response = await client.get("/api/v2/market/klines", headers=auth())
    assert response.status == 200
    body = await response.json()
    assert body["configured"] is False
    assert body["candles"] == []


async def test_workspace_tools_include_emit_result(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        "mokli.agent_api.routes.catalog.skill_rows",
        lambda _path=None: {"skills": [{"name": "cron", "enabled": True, "source": "builtin"}]},
    )
    skills = await client.get("/api/v2/workspace/skills", headers=auth())
    assert skills.status == 200
    assert (await skills.json())["skills"][0]["name"] == "cron"

    tools = await client.get("/api/v2/workspace/tools", headers=auth())
    assert tools.status == 200
    names = {row["name"] for row in (await tools.json())["tools"]}
    assert "emit_result" in names


def test_apply_disabled_skills_reaches_the_live_agent() -> None:
    from mokli.agent_api.tool_ref import apply_disabled_skills, bind_agent

    skills = SimpleNamespace(disabled_skills=set())
    subagents = SimpleNamespace(disabled_skills=set())
    bind_agent(SimpleNamespace(context=SimpleNamespace(skills=skills), subagents=subagents))
    try:
        apply_disabled_skills({"cron"})
        assert skills.disabled_skills == {"cron"}
        assert subagents.disabled_skills == {"cron"}
    finally:
        bind_agent(None)


def test_every_gold_tool_has_a_schema(tmp_path) -> None:
    from mokli.agent.tools.context import ToolContext
    from mokli.agent.tools.loader import ToolLoader
    from mokli.agent.tools.registry import ToolRegistry
    from mokli.config.schema import ToolsConfig

    expected = {
        "analyze_gold",
        "capture_gold_chart",
        "create_goal",
        "cron",
        "fast_backtest",
        "fetch_evidence",
        "get_gate_report",
        "get_gold_quote",
        "get_live_recommendation",
        "gold_intel_scan",
        "list_sessions",
        "manage_trading_plan",
        "message",
        "mt5_cancel_order",
        "mt5_close_position",
        "mt5_confirm_order",
        "mt5_get_account",
        "mt5_list_symbols",
        "mt5_market",
        "mt5_modify_order",
        "mt5_propose_order",
        "propose_strategy",
        "read_session",
        "run_trading_kernel",
        "run_trading_team",
        "search_sessions",
        "send_session_message",
        "spawn",
        "update_goal",
        "web_fetch",
        "web_search",
    }
    ctx = ToolContext(
        config=ToolsConfig(),
        workspace=str(tmp_path),
        bus=MagicMock(),
        subagent_manager=MagicMock(),
        cron_service=MagicMock(),
        sessions=MagicMock(),
        timezone="UTC",
        runtime_control=MagicMock(),
    )
    registry = ToolRegistry()
    registered = set(ToolLoader().load(ctx, registry))
    missing = expected - registered
    assert not missing, missing
    for name in expected:
        tool = registry.get(name)
        assert tool is not None
        schema = tool.to_schema()
        function = schema.get("function", schema)
        assert function.get("name") == name
        assert isinstance(function.get("description"), str) and function["description"].strip()
        assert isinstance(function.get("parameters"), dict)
