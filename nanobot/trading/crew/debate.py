"""Bull/bear debate crew with real team subagents."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Literal

from nanobot.trading.agents.market_data import run_market_data_agent
from nanobot.trading.orchestrator import run_unified_chart_agent
from nanobot.trading.teams.evidence_text import format_market_evidence
from nanobot.trading.teams.subagent_runner import TeamRunCollector, run_team_role

DebateRole = Literal["technical", "fundamental", "bull", "bear", "risk"]


@dataclass
class DebateMessage:
    role: DebateRole
    content: str
    round: int


@dataclass
class DebateResult:
    messages: list[DebateMessage] = field(default_factory=list)
    final: Any | None = None


def _debate_briefing(messages: list[DebateMessage]) -> str:
    lines = ["Debate crew notes:"]
    for msg in messages:
        lines.append(f"- {msg.role} (r{msg.round}): {msg.content[:600]}")
    return "\n".join(lines)


async def run_debate_crew(
    *,
    user_message: str = "",
    emit: Any = None,
    subagent_manager: Any | None = None,
    publisher: Any | None = None,
    interval: str = "15m",
) -> DebateResult:
    market = await asyncio.to_thread(run_market_data_agent, "XAUUSD", interval)
    evidence_text = format_market_evidence(market)
    operator = (user_message or "").strip()
    collector = TeamRunCollector()

    technical = await run_team_role(
        agent_id="technical",
        role="Technical Analyst",
        task_text=f"Technical read for XAUUSD. Operator asked: {operator[:300]}",
        evidence_text=evidence_text,
        manager=subagent_manager,
        publisher=publisher,
        layer=0,
        collector=collector,
    )
    messages = [DebateMessage(role="technical", content=technical, round=0)]

    bull, bear = await asyncio.gather(
        run_team_role(
            agent_id="bull",
            role="Bull Advocate",
            task_text=(
                f"Build the bullish case.\nTechnical note:\n{technical}\n"
                f"Operator: {operator[:200]}"
            ),
            evidence_text=evidence_text,
            manager=subagent_manager,
            publisher=publisher,
            layer=1,
            collector=collector,
        ),
        run_team_role(
            agent_id="bear",
            role="Bear Advocate",
            task_text=(
                f"Build the bearish case.\nTechnical note:\n{technical}\n"
                f"Operator: {operator[:200]}"
            ),
            evidence_text=evidence_text,
            manager=subagent_manager,
            publisher=publisher,
            layer=1,
            collector=collector,
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
            f"Bull:\n{bull}\n\nBear:\n{bear}"
        ),
        evidence_text=evidence_text,
        manager=subagent_manager,
        publisher=publisher,
        layer=2,
        collector=collector,
    )
    messages.append(DebateMessage(role="risk", content=risk, round=2))

    stage_emit = emit
    if publisher is not None and stage_emit is None:
        stage_emit = publisher.sync_emit

    final = await run_unified_chart_agent(
        interval=interval,
        team_mode="debate",
        team_briefing=_debate_briefing(messages),
        emit=stage_emit,
    )
    final.team_agents = list(collector.agents)
    return DebateResult(messages=messages, final=final)
