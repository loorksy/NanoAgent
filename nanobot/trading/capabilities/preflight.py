"""Optional single-role capability preflight before the trading kernel."""

from __future__ import annotations

from typing import Any

from nanobot.trading.agents.market_data import run_market_data_agent
from nanobot.trading.capabilities.catalog import get_card
from nanobot.trading.gold import DATA_SYMBOL
from nanobot.trading.teams.evidence_text import format_market_evidence
from nanobot.trading.teams.subagent_runner import run_team_role
from nanobot.trading.turn_planner import TurnPlan


async def run_capability_preflight(
    turn: TurnPlan,
    *,
    subagent_manager: Any | None = None,
    publisher: Any | None = None,
    interval: str = "15m",
) -> str | None:
    """Run at most one optional subagent brief for macro/structure capability cards."""
    if subagent_manager is None or not turn.capability_cards:
        return None

    for card_id in turn.capability_cards:
        card = get_card(card_id)
        if not card.spawn_role:
            continue
        market = run_market_data_agent(DATA_SYMBOL, interval)
        if not market.sync.ok:
            return None
        evidence_text = format_market_evidence(market)
        summary = await run_team_role(
            agent_id=card_id,
            role=card.spawn_role,
            task_text=card.preflight_prompt or card.spawn_role,
            evidence_text=evidence_text,
            manager=subagent_manager,
            publisher=publisher,
        )
        return f"Capability preflight ({card_id}):\n{summary[:4000]}"
    return None
