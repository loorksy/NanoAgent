"""Vibe-Trading-style YAML DAG swarm executor."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from pathlib import Path
from typing import Any

import yaml

from nanobot.trading.agents.macro_drivers import format_team_briefing, run_macro_drivers
from nanobot.trading.orchestrator import run_unified_chart_agent
from nanobot.trading.stage_events import emit_stage
from nanobot.trading.teams.models import SwarmAgent, SwarmPreset, SwarmTask

_PRESETS_DIR = Path(__file__).parent / "presets"


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


async def run_swarm(
    preset_name: str,
    variables: dict[str, str] | None = None,
    *,
    macro_search: Any | None = None,
    macro_events: list[dict[str, Any]] | None = None,
    macro_now: Any | None = None,
) -> dict[str, Any]:
    preset = load_preset(preset_name)
    vars_ = {"target": "XAUUSD", "market": "forex", **(variables or {})}
    summaries: dict[str, str] = {}
    layers = topological_layers(preset.tasks)

    for layer in layers:
        async def run_task(task: SwarmTask) -> tuple[str, str]:
            upstream = "\n".join(
                f"{key}: {summaries[src]}" for key, src in task.input_from.items() if src in summaries
            )
            agent = next((a for a in preset.agents if a.id == task.agent_id), None)
            role = agent.role if agent else task.agent_id
            prompt = task.prompt_template.format(**vars_, upstream_context=upstream)
            return task.id, f"[{role}] {prompt[:500]}"

        results = await asyncio.gather(*[run_task(t) for t in layer])
        for task_id, summary in results:
            summaries[task_id] = summary

    started = time.time()
    verdicts = await run_macro_drivers(
        search=macro_search,
        events=macro_events,
        now=macro_now,
    )
    briefing = format_team_briefing(verdicts)
    final = await run_unified_chart_agent(
        team_mode=f"swarm:{preset_name}",
        team_briefing=briefing,
    )
    final.macro_drivers = [item.to_wire() for item in verdicts]
    duration_ms = int((time.time() - started) * 1000)
    final.stages = list(final.stages or [])
    final.stages.append(
        emit_stage("macro_drivers", "done", duration_ms=duration_ms).to_wire()
    )
    return {
        "preset": preset_name,
        "task_summaries": summaries,
        "macro_drivers": final.macro_drivers,
        "final": final,
    }
