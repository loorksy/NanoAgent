import json
from unittest.mock import MagicMock

from websockets.http11 import Request

from nanobot.agent.tools.context import RequestContext, current_request_context, request_context
from nanobot.providers.base import GenerationSettings, LLMProvider
from nanobot.trading.types import AgentFinalResult, AgentRecommendation, FinalDecisionResult
from nanobot.utils.llm_runtime import LLMRuntime
from nanobot.webui.trading_api import (
    analyze_request_context,
    handle_trading_analyze,
    handle_trading_klines,
    handle_trading_performance,
    handle_trading_status,
)


def _request(path: str) -> Request:
    return Request(path, [])


def test_trading_status_without_oanda() -> None:
    response = handle_trading_status(_request("/api/trading/status"))
    assert response.status_code == 200
    body = response.body.decode("utf-8")
    assert "XAUUSD" in body
    assert "oanda_configured" in body


def test_trading_performance_payload() -> None:
    response = handle_trading_performance(_request("/api/trading/performance"))
    assert response.status_code == 200
    body = response.body.decode("utf-8")
    assert "totalRecommendations" in body
    assert "paperActions" in body


def test_trading_klines_unconfigured() -> None:
    response = handle_trading_klines(
        _request("/api/trading/klines?symbol=XAUUSD&interval=1h&limit=10"),
    )
    assert response.status_code == 200
    body = response.body.decode("utf-8")
    assert "candles" in body


def _fake_runtime(model: str = "test-model") -> LLMRuntime:
    provider = MagicMock(spec=LLMProvider)
    provider.generation = GenerationSettings()
    return LLMRuntime.capture(provider, model, context_window_tokens=128_000)


def _fake_final(*, decision: str = "sell", confidence: float = 0.56) -> AgentFinalResult:
    return AgentFinalResult(
        decision=FinalDecisionResult(
            decision=decision,
            confidence=confidence,
            summary=f"{decision} stub",
            key_reasons=[],
            risk_warnings=[],
            recommendation=AgentRecommendation(action=decision, interval="15m"),
        ),
        team_mode="swarm:gold_analysis_committee",
        stages=[],
    )


def test_analyze_request_context_uses_configured_provider(monkeypatch) -> None:
    runtime = _fake_runtime()
    monkeypatch.setattr("nanobot.webui.trading_api.load_provider_snapshot", lambda: object())
    monkeypatch.setattr(
        "nanobot.webui.trading_api.runtime_from_provider_snapshot",
        lambda _snapshot: runtime,
    )
    ctx = analyze_request_context()
    assert ctx.runtime is runtime
    assert ctx.channel == "webui"


def test_analyze_request_context_absent_provider(monkeypatch) -> None:
    def _boom() -> None:
        raise ValueError("No API key configured for provider 'anthropic'.")

    monkeypatch.setattr("nanobot.webui.trading_api.load_provider_snapshot", _boom)
    ctx = analyze_request_context()
    assert ctx.runtime is None


def test_analyze_request_context_fills_missing_runtime(monkeypatch) -> None:
    runtime = _fake_runtime()
    monkeypatch.setattr("nanobot.webui.trading_api.load_provider_snapshot", lambda: object())
    monkeypatch.setattr(
        "nanobot.webui.trading_api.runtime_from_provider_snapshot",
        lambda _snapshot: runtime,
    )
    with request_context(RequestContext(channel="cli", chat_id="direct")):
        ctx = analyze_request_context()
    assert ctx.runtime is runtime
    assert ctx.channel == "cli"


def test_analyze_request_context_keeps_existing_runtime(monkeypatch) -> None:
    existing_runtime = _fake_runtime("already-bound")
    loaded_runtime = _fake_runtime("should-not-load")
    monkeypatch.setattr(
        "nanobot.webui.trading_api.runtime_from_provider_snapshot",
        lambda _snapshot: loaded_runtime,
    )
    with request_context(
        RequestContext(channel="cli", chat_id="direct", runtime=existing_runtime)
    ):
        ctx = analyze_request_context()
    assert ctx.runtime is existing_runtime
    assert ctx.channel == "cli"


def test_http_analyze_swarm_binds_llm_runtime_across_thread(monkeypatch) -> None:
    runtime = _fake_runtime()
    monkeypatch.setattr(
        "nanobot.webui.trading_api.create_trading_subagent_manager",
        lambda: MagicMock(),
    )
    monkeypatch.setattr("nanobot.webui.trading_api.load_provider_snapshot", lambda: object())
    monkeypatch.setattr(
        "nanobot.webui.trading_api.runtime_from_provider_snapshot",
        lambda _snapshot: runtime,
    )
    seen: dict[str, object] = {}

    async def fake_swarm(preset, **kwargs):
        ctx = current_request_context()
        seen["preset"] = preset
        seen["runtime"] = ctx.runtime if ctx else None
        return {"final": _fake_final()}

    monkeypatch.setattr("nanobot.webui.trading_api.run_swarm", fake_swarm)
    response = handle_trading_analyze(
        _request("/api/trading/analyze?team_mode=swarm"),
    )
    assert response.status_code == 200
    assert seen["preset"] == "gold_analysis_committee"
    assert seen["runtime"] is runtime


def test_http_analyze_core_binds_llm_runtime(monkeypatch) -> None:
    runtime = _fake_runtime()
    monkeypatch.setattr(
        "nanobot.webui.trading_api.create_trading_subagent_manager",
        lambda: MagicMock(),
    )
    monkeypatch.setattr("nanobot.webui.trading_api.load_provider_snapshot", lambda: object())
    monkeypatch.setattr(
        "nanobot.webui.trading_api.runtime_from_provider_snapshot",
        lambda _snapshot: runtime,
    )
    seen: dict[str, object] = {}

    async def fake_core(*, interval: str, team_mode: str):
        ctx = current_request_context()
        seen["runtime"] = ctx.runtime if ctx else None
        seen["team_mode"] = team_mode
        seen["interval"] = interval
        return _fake_final(decision="wait", confidence=0.0)

    monkeypatch.setattr("nanobot.webui.trading_api.run_unified_chart_agent", fake_core)
    response = handle_trading_analyze(
        _request("/api/trading/analyze?interval=15m&team_mode=core"),
    )
    assert response.status_code == 200
    assert seen["runtime"] is runtime
    assert seen["team_mode"] == "core"
    assert seen["interval"] == "15m"


def test_http_analyze_debate_binds_llm_runtime(monkeypatch) -> None:
    runtime = _fake_runtime()
    monkeypatch.setattr(
        "nanobot.webui.trading_api.create_trading_subagent_manager",
        lambda: MagicMock(),
    )
    monkeypatch.setattr("nanobot.webui.trading_api.load_provider_snapshot", lambda: object())
    monkeypatch.setattr(
        "nanobot.webui.trading_api.runtime_from_provider_snapshot",
        lambda _snapshot: runtime,
    )
    seen: dict[str, object] = {}

    async def fake_debate(**kwargs):
        ctx = current_request_context()
        seen["runtime"] = ctx.runtime if ctx else None
        return MagicMock(final=_fake_final(decision="wait", confidence=0.1))

    monkeypatch.setattr("nanobot.webui.trading_api.run_debate_crew", fake_debate)
    response = handle_trading_analyze(
        _request("/api/trading/analyze?team_mode=debate"),
    )
    assert response.status_code == 200
    assert seen["runtime"] is runtime
