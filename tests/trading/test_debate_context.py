"""Debate roles receive scoped evidence and a short upstream note."""

from __future__ import annotations

import json

import pytest

from mokli.trading.types import AgentMarketContext, Candle, MarketSync
from mokli.utils.helpers import estimate_prompt_tokens


def _market() -> AgentMarketContext:
    candles = []
    for index in range(40):
        close = 2300.0 + index
        candles.append(
            Candle(
                time_ms=1_700_000_000_000 + index,
                open=close,
                high=close + 1,
                low=close - 1,
                close=close,
                volume=1,
                complete=True,
            )
        )
    return AgentMarketContext(
        symbol="XAUUSD",
        interval="15m",
        candles=candles,
        last_close=candles[-1].close,
        atr=2.5,
        sync=MarketSync(ok=True),
        quote_mid=candles[-1].close,
    )


@pytest.mark.asyncio
async def test_debate_does_not_resend_candles_or_the_full_note(monkeypatch) -> None:
    from mokli.trading.crew.debate import run_debate_crew

    seen: list[tuple[str, str, str]] = []
    raw = ("level " * 900).strip() + "\nSTANCE: sell"

    async def fake_role(**kwargs: object) -> str:
        seen.append(
            (
                str(kwargs.get("role")),
                str(kwargs.get("evidence_text")),
                str(kwargs.get("task_text")),
            )
        )
        return raw

    monkeypatch.setattr("mokli.trading.crew.debate.run_team_role", fake_role)
    monkeypatch.setattr(
        "mokli.trading.crew.debate.run_market_data_agent",
        lambda *_args, **_kwargs: _market(),
    )

    result = await run_debate_crew(user_message="هل أشتري الذهب؟")
    by_role = {role: (evidence, task) for role, evidence, task in seen}
    technical_evidence, _technical_task = by_role["Technical Analyst"]
    bull_evidence, bull_task = by_role["Bull Advocate"]
    bear_evidence, bear_task = by_role["Bear Advocate"]
    risk_evidence, risk_task = by_role["Risk Manager"]

    assert "candles" in json.loads(technical_evidence)
    for evidence in (bull_evidence, bear_evidence, risk_evidence):
        parsed = json.loads(evidence)
        assert "candles" not in parsed
        assert parsed["quote_mid"] == _market().quote_mid
    assert raw not in bull_task
    assert raw not in bear_task
    assert raw not in risk_task
    assert "STANCE: sell" in bull_task
    assert "STANCE: sell" in risk_task
    assert "STANCE: sell" in result.briefing

    operator = "هل أشتري الذهب؟"
    old_bull = (
        f"Build the bullish case.\nTechnical note:\n{raw}\nOperator: {operator[:200]}"
    )
    old_bear = (
        f"Build the bearish case.\nTechnical note:\n{raw}\nOperator: {operator[:200]}"
    )
    old_risk = (
        "Reconcile bull and bear cases. State whether a plan is worth gating.\n"
        f"Bull:\n{raw}\n\nBear:\n{raw}"
    )
    before = estimate_prompt_tokens(
        [
            {"role": "user", "content": technical_evidence},
            {"role": "user", "content": technical_evidence},
            {"role": "user", "content": technical_evidence},
            {"role": "user", "content": old_bull},
            {"role": "user", "content": old_bear},
            {"role": "user", "content": old_risk},
        ]
    )
    after = estimate_prompt_tokens(
        [
            {"role": "user", "content": bull_evidence},
            {"role": "user", "content": bear_evidence},
            {"role": "user", "content": risk_evidence},
            {"role": "user", "content": bull_task},
            {"role": "user", "content": bear_task},
            {"role": "user", "content": risk_task},
        ]
    )
    assert after < before
    print(f"TOKEN_DEBATE before={before} after={after}")


@pytest.mark.asyncio
async def test_debate_roles_publish_on_the_activity_bus(monkeypatch) -> None:
    """Roles that run are visible. A missing session still runs and publishes nothing."""
    from unittest.mock import AsyncMock, MagicMock

    from mokli.agent.tools.context import RequestContext, request_context
    from mokli.events import TeamRoleEvent
    from mokli.utils.llm_runtime import LLMRuntime
    from mokli.trading.crew.debate import run_debate_crew
    from mokli.trading.teams.role_display import role_phrase

    monkeypatch.setattr(
        "mokli.trading.crew.debate.run_market_data_agent",
        lambda *_args, **_kwargs: _market(),
    )
    provider = MagicMock()
    provider.chat = AsyncMock(return_value=MagicMock(content="STANCE: wait"))
    runtime = LLMRuntime.capture(provider, "test-model", context_window_tokens=128_000)
    bus = MagicMock()
    bus.publish = AsyncMock()

    with request_context(
        RequestContext(
            channel="agent_api",
            chat_id="chat",
            session_key="agent_api:chat",
            runtime=runtime,
        )
    ):
        await run_debate_crew(user_message="buy gold", bus=bus)

    events = [call.args[0] for call in bus.publish.await_args_list]
    assert all(isinstance(event, TeamRoleEvent) for event in events)
    by_role: dict[str, list[str]] = {}
    for event in events:
        by_role.setdefault(event.role, []).append(event.status)
        assert event.display == role_phrase(event.role, event.status)
        assert event.session_key == "agent_api:chat"
    assert by_role == {
        "Technical Analyst": ["running", "done"],
        "Bull Advocate": ["running", "done"],
        "Bear Advocate": ["running", "done"],
        "Risk Manager": ["running", "done"],
    }
    assert provider.chat.await_count == 4

    bus.publish.reset_mock()
    with request_context(
        RequestContext(channel="websocket", chat_id="1", runtime=runtime)
    ):
        await run_debate_crew(user_message="buy gold", bus=bus)
    bus.publish.assert_not_awaited()
