import pytest

from nanobot.trading.orchestrator import run_unified_chart_agent


@pytest.mark.asyncio
async def test_run_unified_chart_agent_returns_result():
    result = await run_unified_chart_agent(store=False)
    assert result.decision is not None
    assert result.decision.decision in ("buy", "sell", "wait")
    assert isinstance(result.stages, list)
