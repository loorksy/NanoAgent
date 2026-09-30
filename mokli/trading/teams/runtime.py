"""YAML DAG swarm executor with real team subagents.

Teams are invoked only as tools by the agent (``run_trading_team`` /
``analyze_gold(team_mode=swarm)``). They produce briefs; ``run_trading_kernel``
is the only path that turns a brief into a BUY/SELL decision.
"""

from __future__ import annotations

import asyncio
import re
import time
from collections import deque
from pathlib import Path
from typing import Any

import yaml

from mokli.trading.agents.macro_drivers import format_team_briefing, run_macro_drivers
from mokli.trading.agents.market_data import run_market_data_agent
from mokli.trading.i18n import tr
from mokli.trading.market_context import build_agent_market_context
from mokli.trading.stage_events import emit_stage
from mokli.trading.teams.evidence_text import (
    compact_timeframe_window,
    evidence_with_macro_drivers,
    format_market_evidence,
    named_chart_interval,
    scope_market_evidence,
    trend_evidence,
)
from mokli.trading.teams.models import SwarmAgent, SwarmPreset, SwarmTask
from mokli.trading.teams.role_prompts import resolve_role_file
from mokli.trading.teams.subagent_runner import TeamRunCollector, run_team_role

_PRESETS_DIR = Path(__file__).parent / "presets"
_STANCE_LINE = re.compile(r"(?im)^STANCE:\s*(buy|sell|wait)\s*$")
_UPSTREAM_LIMIT = 400
# Same window ``run_multi_timeframe_agent`` loads, so a team role joins that cache.
_HIGHER_TF_LIMIT = 120
_HIGHER_TIMEFRAMES = ("1h", "4h", "1d")
# These roles read the driver list. Other roles get the short stance, not the list.
# Event analysis ranks those same items; a 400-character upstream note drops them.
_MACRO_EVIDENCE_FILES = frozenset({"macro", "news", "event"})


async def _timed_macro_drivers(
    *,
    search: Any | None,
    events: list[dict[str, Any]] | None,
    now: Any | None,
) -> tuple[list[Any], int]:
    """Time the macro searches themselves, not the wait for team roles."""
    started = time.perf_counter()
    verdicts = await run_macro_drivers(search=search, events=events, now=now)
    return list(verdicts), int((time.perf_counter() - started) * 1000)


def explicit_stances(summaries: dict[str, str]) -> list[str]:
    """Stance words actually published. A note without the line is not a vote."""
    found: list[str] = []
    for text in summaries.values():
        match = _STANCE_LINE.search(text or "")
        if match:
            found.append(match.group(1).lower())
    return found


def review_needed(summaries: dict[str, str]) -> bool:
    """A review round is warranted when two or more stances disagree."""
    stances = explicit_stances(summaries)
    if len(stances) < 2:
        return False
    return len(set(stances)) > 1


def _is_conflict_review(role: str, system_prompt: str) -> bool:
    return "review" in role.lower() and resolve_role_file(role, system_prompt) == "lead"


def brief_for_upstream(summary: str, *, limit: int = _UPSTREAM_LIMIT) -> str:
    """Short brief for the next role. The stance line is kept even when the body is cut."""
    text = (summary or "").strip()
    if not text:
        return ""
    match = _STANCE_LINE.search(text)
    stance = match.group(0).strip() if match else ""
    head = text if len(text) <= limit else text[:limit].rstrip() + "…"
    if stance and stance not in head:
        return f"{head}\n{stance}"
    return head


async def evidence_for_team_role(
    lead_evidence: str,
    role: str,
    system_prompt: str,
) -> str:
    """Evidence one role reads.

    H1, H4, and D1 each load their own candles. A trend role gets the lead
    quote and a short window for those three charts, not a second copy of the
    lead bars and not a live quote per chart. Structure roles keep the lead
    candle list.
    """
    named = named_chart_interval(role)
    if named is not None:
        market = await asyncio.to_thread(
            build_agent_market_context,
            "XAUUSD",
            named,
            _HIGHER_TF_LIMIT,
        )
        return format_market_evidence(market)
    if resolve_role_file(role, system_prompt) == "timeframe":

        async def _window(interval: str) -> dict[str, object]:
            market = await asyncio.to_thread(
                build_agent_market_context,
                "XAUUSD",
                interval,
                _HIGHER_TF_LIMIT,
                include_quote=False,
            )
            return compact_timeframe_window(market)

        windows = list(await asyncio.gather(*[_window(interval) for interval in _HIGHER_TIMEFRAMES]))
        return trend_evidence(lead_evidence, windows)
    return scope_market_evidence(lead_evidence, role, system_prompt)


def list_presets() -> list[str]:
    return sorted(path.stem for path in _PRESETS_DIR.glob("*.yaml"))


def load_preset(name: str) -> SwarmPreset:
    path = _PRESETS_DIR / f"{name}.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    agents = [SwarmAgent(**a) for a in raw.get("agents", [])]
    tasks = [SwarmTask(**t) for t in raw.get("tasks", [])]
    return SwarmPreset(
        name=raw.get("name", name),
        title=raw.get("title", name),
        description=raw.get("description", ""),
        agents=agents,
        tasks=tasks,
        variables=raw.get("variables", []),
    )


def topological_layers(tasks: list[SwarmTask]) -> list[list[SwarmTask]]:
    deps: dict[str, set[str]] = {t.id: set(t.depends_on) for t in tasks}
    indegree = {t.id: len(deps[t.id]) for t in tasks}
    by_id = {t.id: t for t in tasks}
    layers: list[list[SwarmTask]] = []
    ready = deque([tid for tid, d in indegree.items() if d == 0])
    while ready:
        layer_ids = list(ready)
        ready.clear()
        layers.append([by_id[tid] for tid in layer_ids])
        for tid in layer_ids:
            for other_id, other_deps in deps.items():
                if tid in other_deps:
                    other_deps.remove(tid)
                    indegree[other_id] -= 1
                    if indegree[other_id] == 0:
                        ready.append(other_id)
    return layers


def _format_swarm_briefing(
    preset_name: str,
    task_summaries: dict[str, str],
    macro_briefing: str,
) -> str:
    lines = [tr("team.swarm_preset", preset=preset_name)]
    for task_id, summary in task_summaries.items():
        lines.append(f"- {task_id}: {brief_for_upstream(summary, limit=500)}")
    if macro_briefing:
        lines.append("")
        lines.append(macro_briefing)
    return "\n".join(lines)


async def run_swarm(
    preset_name: str,
    variables: dict[str, str] | None = None,
    *,
    macro_search: Any | None = None,
    macro_events: list[dict[str, Any]] | None = None,
    macro_now: Any | None = None,
    subagent_manager: Any | None = None,
    publisher: Any | None = None,
    bus: Any | None = None,
    interval: str = "15m",
    emit: Any | None = None,
    visual_capture: Any = None,
    max_review_rounds: int = 1,
) -> dict[str, Any]:
    """Run every role of a preset and return their briefs (never a BUY/SELL).

    A conflict review runs only when prior stances disagree, and at most
    ``max_review_rounds`` times. Agreement does not call that role.

    ``emit`` and ``visual_capture`` are accepted for call-site compatibility; the
    caller passes the returned ``team_briefing`` to ``run_trading_kernel``.
    """
    preset = load_preset(preset_name)
    vars_ = {"target": "XAUUSD", "market": "forex", **(variables or {})}
    summaries: dict[str, str] = {}
    layers = topological_layers(preset.tasks)
    collector = TeamRunCollector()

    market = await asyncio.to_thread(run_market_data_agent, "XAUUSD", interval)
    evidence_text = format_market_evidence(market)
    # Macro searches do not read role summaries. Start them with the first layer.
    macro_task = asyncio.create_task(
        _timed_macro_drivers(
            search=macro_search,
            events=macro_events,
            now=macro_now,
        )
    )

    try:
        for layer_index, layer in enumerate(layers):

            async def run_task(task: SwarmTask) -> tuple[str, str | None]:
                upstream = "\n".join(
                    f"{key}: {brief_for_upstream(summaries[src])}"
                    for key, src in task.input_from.items()
                    if src in summaries
                )
                agent = next((a for a in preset.agents if a.id == task.agent_id), None)
                role = agent.role if agent else task.agent_id
                system_prompt = agent.system_prompt if agent else ""
                if _is_conflict_review(role, system_prompt) and (
                    max_review_rounds < 1 or not review_needed(summaries)
                ):
                    return task.id, None
                prompt = task.prompt_template.format(**vars_, upstream_context=upstream)
                role_evidence = await evidence_for_team_role(
                    evidence_text,
                    role,
                    system_prompt,
                )
                if resolve_role_file(role, system_prompt) in _MACRO_EVIDENCE_FILES:
                    driver_verdicts, _macro_ms = await macro_task
                    role_evidence = evidence_with_macro_drivers(
                        role_evidence,
                        format_team_briefing(driver_verdicts),
                    )
                summary = await run_team_role(
                    agent_id=task.agent_id,
                    role=role,
                    task_text=prompt,
                    evidence_text=role_evidence,
                    system_prompt=system_prompt,
                    manager=subagent_manager,
                    publisher=publisher,
                    layer=layer_index,
                    collector=collector,
                    bus=bus,
                )
                return task.id, summary

            results = await asyncio.gather(*[run_task(task) for task in layer])
            for task_id, summary in results:
                if summary is None:
                    continue
                summaries[task_id] = summary
        verdicts, duration_ms = await macro_task
    finally:
        if not macro_task.done():
            macro_task.cancel()
            try:
                await macro_task
            except asyncio.CancelledError:
                pass

    macro_briefing = format_team_briefing(verdicts)
    team_briefing = _format_swarm_briefing(preset_name, summaries, macro_briefing)
    return {
        "preset": preset_name,
        "task_summaries": summaries,
        "macro_drivers": [item.to_wire() for item in verdicts],
        "team_briefing": team_briefing,
        "team_agents": list(collector.agents),
        "final": None,
        "stages": [emit_stage("macro_drivers", "done", duration_ms=duration_ms).to_wire()],
    }
