"""Run trading team roles via SubagentManager or a direct LLM fallback."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from loguru import logger

from mokli.agent.tools.context import current_request_context
from mokli.events import TeamRoleEvent
from mokli.security.workspace_access import current_workspace_scope
from mokli.trading.i18n import tr
from mokli.trading.teams.role_prompts import role_system_prompt

if TYPE_CHECKING:
    from mokli.agent.subagent import SubagentManager
    from mokli.bus.queue import MessageBus
    from mokli.trading.stage_delivery import TradingStagePublisher
    from mokli.utils.llm_runtime import LLMRuntime


def create_trading_subagent_manager(bus: MessageBus | None = None) -> SubagentManager:
    """Build a SubagentManager for trading team runs outside AgentLoop."""
    from mokli.agent.subagent import SubagentManager
    from mokli.bus.queue import MessageBus as Bus
    from mokli.config.paths import get_workspace_path
    from mokli.config.schema import AgentDefaults

    defaults = AgentDefaults()
    return SubagentManager(
        workspace=get_workspace_path(),
        bus=bus if bus is not None else Bus(),
        max_tool_result_chars=defaults.max_tool_result_chars,
        max_concurrent_subagents=defaults.max_concurrent_subagents,
    )

TeamAgentStatus = Literal["running", "done", "failed"]


@dataclass(frozen=True)
class TeamAgentEvent:
    agent_id: str
    role: str
    status: TeamAgentStatus
    summary: str = ""
    layer: int = 0
    duration_ms: int | None = None

    def to_wire(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "agentId": self.agent_id,
            "role": self.role,
            "status": self.status,
            "summary": self.summary,
            "layer": self.layer,
        }
        if self.duration_ms is not None:
            payload["durationMs"] = self.duration_ms
        return payload


@dataclass
class TeamRunCollector:
    """Accumulates team agent timeline events for the final wire payload."""

    agents: list[dict[str, Any]] = field(default_factory=list)

    def record(self, event: TeamAgentEvent) -> None:
        wire = event.to_wire()
        for index, row in enumerate(self.agents):
            if row.get("agentId") == wire.get("agentId"):
                self.agents[index] = wire
                return
        self.agents.append(wire)


async def _publish_runtime_role(bus: Any | None, event: TeamAgentEvent) -> None:
    """Mirror a role that actually ran onto the agent bus for the activity line."""
    if bus is None:
        return
    request = current_request_context()
    session_key = request.session_key if request is not None else None
    if not session_key:
        return
    await bus.publish(
        TeamRoleEvent(
            session_key=session_key,
            agent_id=event.agent_id,
            role=event.role,
            status=event.status,
            summary=event.summary,
            duration_ms=event.duration_ms,
        )
    )


async def _publish_team_agent(
    publisher: TradingStagePublisher | None,
    event: TeamAgentEvent,
    collector: TeamRunCollector | None = None,
    bus: Any | None = None,
) -> None:
    if collector is not None:
        collector.record(event)
    await _publish_runtime_role(bus, event)
    if publisher is None:
        return
    await publisher.publish_team_agent(event.to_wire())


def resolve_role_prompt(role: str, system_prompt: str = "") -> str:
    """System prompt for one team role.

    The preset YAML ``system_prompt`` wins (``role_prompts`` resolves ``role:<file>``
    references); an empty field falls back to the role-label mapping.
    """
    return role_system_prompt(role, system_prompt=(system_prompt or "").strip())


async def _llm_complete(
    role: str,
    task_text: str,
    runtime: LLMRuntime,
    *,
    system_prompt: str = "",
) -> str:
    messages = [
        {"role": "system", "content": resolve_role_prompt(role, system_prompt)},
        {"role": "user", "content": task_text},
    ]
    response = await runtime.provider.chat(
        messages=messages,
        model=runtime.model,
        max_tokens=1024,
        temperature=0.2,
    )
    return (getattr(response, "content", None) or "").strip()


async def run_team_role(
    *,
    agent_id: str,
    role: str,
    task_text: str,
    evidence_text: str,
    system_prompt: str = "",
    manager: SubagentManager | None = None,
    publisher: TradingStagePublisher | None = None,
    layer: int = 0,
    collector: TeamRunCollector | None = None,
    bus: Any | None = None,
) -> str:
    """Execute one team role and return its textual summary.

    ``system_prompt`` is the preset's role instruction. When the turn has a
    model runtime, the role is one completion with that instruction and the
    frozen evidence, and no tool list. The subagent manager is only the
    fallback when that runtime is missing.
    """
    request = current_request_context()
    runtime = request.runtime if request else None
    started = time.time()

    role_prompt = resolve_role_prompt(role, system_prompt)
    task_body = (
        f"{task_text.strip()}\n\n"
        f"FROZEN MARKET EVIDENCE (do not invent prices outside this JSON):\n"
        f"{evidence_text[:12000]}"
    )
    full_task = f"ROLE INSTRUCTIONS:\n{role_prompt}\n\nTASK:\n{task_body}"

    await _publish_team_agent(
        publisher,
        TeamAgentEvent(agent_id=agent_id, role=role, status="running", layer=layer),
        collector,
        bus,
    )

    try:
        if runtime is not None:
            summary = await _llm_complete(
                role,
                task_body,
                runtime,
                system_prompt=system_prompt,
            )
        elif manager is not None and request is not None:
            summary = await manager.run_inline(
                task=full_task,
                label=role,
                runtime=runtime,
                origin_channel=request.channel,
                origin_chat_id=request.chat_id,
                session_key=request.session_key,
                origin_message_id=request.message_id,
                workspace_scope=current_workspace_scope(),
            )
            if summary.startswith("Error:"):
                raise RuntimeError(summary)
        else:
            raise RuntimeError(tr("team.no_llm_runtime"))

        summary = summary.strip() or tr("team.no_summary", role=role)
        duration_ms = int((time.time() - started) * 1000)
        await _publish_team_agent(
            publisher,
            TeamAgentEvent(
                agent_id=agent_id,
                role=role,
                status="done",
                summary=summary[:2000],
                layer=layer,
                duration_ms=duration_ms,
            ),
            collector,
            bus,
        )
        return summary
    except Exception as exc:
        logger.warning("Team agent {} ({}) failed: {}", agent_id, role, exc)
        duration_ms = int((time.time() - started) * 1000)
        message = tr("team.agent_failed", role=role, error=exc)
        await _publish_team_agent(
            publisher,
            TeamAgentEvent(
                agent_id=agent_id,
                role=role,
                status="failed",
                summary=message,
                layer=layer,
                duration_ms=duration_ms,
            ),
            collector,
            bus,
        )
        return message
