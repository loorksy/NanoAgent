"""Foxagent-style bull/bear debate pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from nanobot.trading.orchestrator import run_unified_chart_agent
from nanobot.trading.stage_events import StageEvent, emit_stage
from nanobot.trading.types import AgentFinalResult

DebateRole = Literal["technical", "fundamental", "bull", "bear", "risk"]


@dataclass
class DebateMessage:
    role: DebateRole
    content: str
    round: int


@dataclass
class DebateResult:
    messages: list[DebateMessage] = field(default_factory=list)
    final: AgentFinalResult | None = None


async def run_debate_crew(
    *,
    user_message: str = "",
    emit: Any = None,
) -> DebateResult:
    """Debate crew augments core fleet — core analysis still runs, debate notes captured."""
    messages: list[DebateMessage] = []
    stages: list[StageEvent] = []

    def track(ev: StageEvent) -> None:
        stages.append(ev)
        if emit:
            emit(ev)

    track(emit_stage("research", "running"))
    messages.append(DebateMessage(role="technical", content=f"Analyzing XAUUSD: {user_message[:200]}", round=0))
    messages.append(DebateMessage(role="bull", content="Bull case: structure supports continuation if gates pass.", round=1))
    messages.append(DebateMessage(role="bear", content="Bear case: watch liquidity sweeps and news risk.", round=1))
    messages.append(DebateMessage(role="risk", content="Risk manager: mandatory G1-G7 gates apply.", round=2))
    track(emit_stage("research", "done"))

    final = await run_unified_chart_agent(team_mode="debate", emit=track)
    return DebateResult(messages=messages, final=final)
