import pytest

from nanobot.agent.tools.trading_team import RunTradingTeamTool


@pytest.mark.asyncio
async def test_run_trading_team_disabled() -> None:
    tool = RunTradingTeamTool.create(None)
    result = await tool.execute(preset="gold_analysis_committee")
    assert "not available" in result.lower()
