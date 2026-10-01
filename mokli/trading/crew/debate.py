"""Bull/bear debate crew with real team subagents.

Invoked only as a tool by the agent (``analyze_gold(team_mode=debate)``). The
crew produces a briefing; ``run_trading_kernel`` issues the decision.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Literal

from mokli.trading.agents.market_data import run_market_data_agent
from mokli.trading.teams.evidence_text import format_market_evidence
from mokli.trading.teams.runtime import brief_for_upstream, evidence_for_team_role
from mokli.trading.teams.subagent_runner import TeamRunCollector, run_team_role

DebateRole = Literal["technical", "fundamental", "bull", "bear", "risk"]


@dataclass
class DebateMessage:
    role: DebateRole
    content: str
    round: int


@dataclass
class DebateResult:
    messages: list[DebateMessage] = field(default_factory=list)
    briefing: str = ""
    team_agents: list[dict[str, Any]] = field(default_factory=list)


def _debate_briefing(messages: list[DebateMessage]) -> str:
    lines = ["Debate crew notes:"]
    for msg in messages:
        lines.append(
            f"- {msg.role} (r{msg.round}): {brief_for_upstream(msg.content, limit=500)}"
        )
    return "\n".join(lines)


async def run_debate_crew(
    *,
    user_message: str = "",
    emit: Any = None,
    subagent_manager: Any | None = None,
    publisher: Any | None = None,
    interval: str = "15m",
    visual_capture: Any = None,
    bus: Any | None = None,
) -> DebateResult:
    """Run technical -> bull || bear -> risk and return the briefing (no BUY/SELL).

    ``bus`` publishes each role that actually starts, the same way a swarm does.
    ``emit`` and ``visual_capture`` are accepted for call-site compatibility.
    """
    market = await asyncio.to_thread(run_market_data_agent, "XAUUSD", interval)
    evidence_text = format_market_evidence(market)
    operator = (user_message or "").strip()
    collector = TeamRunCollector()

    async def role_evidence(role: str) -> str:
        return await evidence_for_team_role(evidence_text, role, "", market=market)

    technical_evidence, bull_evidence, bear_evidence, risk_evidence = await asyncio.gather(
        role_evidence("Technical Analyst"),
        role_evidence("Bull Advocate"),
        role_evidence("Bear Advocate"),
        role_evidence("Risk Manager"),
    )

    technical = await run_team_role(
        agent_id="technical",
        role="Technical Analyst",
        task_text=f"Technical read for XAUUSD. Operator asked: {operator[:300]}",
        evidence_text=technical_evidence,
        manager=subagent_manager,
        publisher=publisher,
        layer=0,
        collector=collector,
        bus=bus,
    )
    messages = [DebateMessage(role="technical", content=technical, round=0)]
    technical_note = brief_for_upstream(technical)

    bull, bear = await asyncio.gather(
        run_team_role(
            agent_id="bull",
            role="Bull Advocate",
            task_text=(
                f"Build the bullish case.\nTechnical note:\n{technical_note}\n"
                f"Operator: {operator[:200]}"
            ),
            evidence_text=bull_evidence,
            manager=subagent_manager,
            publisher=publisher,
            layer=1,
            collector=collector,
            bus=bus,
        ),
        run_team_role(
            agent_id="bear",
            role="Bear Advocate",
            task_text=(
                f"Build the bearish case.\nTechnical note:\n{technical_note}\n"
                f"Operator: {operator[:200]}"
            ),
            evidence_text=bear_evidence,
            manager=subagent_manager,
            publisher=publisher,
            layer=1,
            collector=collector,
            bus=bus,
        ),
    )
    messages.extend(
        [
            DebateMessage(role="bull", content=bull, round=1),
            DebateMessage(role="bear", content=bear, round=1),
        ]
    )

    risk = await run_team_role(
        agent_id="risk",
        role="Risk Manager",
        task_text=(
            "Reconcile bull and bear cases. State whether a plan is worth gating.\n"
            f"Bull:\n{brief_for_upstream(bull)}\n\nBear:\n{brief_for_upstream(bear)}"
        ),
        evidence_text=risk_evidence,
        manager=subagent_manager,
        publisher=publisher,
        layer=2,
        collector=collector,
        bus=bus,
    )
    messages.append(DebateMessage(role="risk", content=risk, round=2))

    briefing = _debate_briefing(messages)
    return DebateResult(messages=messages, briefing=briefing, team_agents=list(collector.agents))
