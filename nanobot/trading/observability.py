"""Structured runtime observability — Phase M."""

from __future__ import annotations

import json
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator

from loguru import logger

from nanobot.trading.policy_guard import ValidatedPlan
from nanobot.trading.types import GateChainResult


@dataclass(frozen=True)
class PlannerObservability:
    turn_mode: str
    capability_cards: tuple[str, ...]
    planned_nodes: tuple[str, ...]
    executed_nodes: tuple[str, ...]
    shadow_mode: bool
    adjustments: tuple[str, ...]


@dataclass
class NodeTimingRecord:
    node_id: str
    duration_ms: int
    status: str = "done"


@dataclass
class RuntimeObservability:
    planner: PlannerObservability | None = None
    node_timings: list[NodeTimingRecord] = field(default_factory=list)
    gate_outcome: dict[str, Any] | None = None


def log_planner_observability(validated: ValidatedPlan) -> None:
    payload = PlannerObservability(
        turn_mode=validated.plan.mode,
        capability_cards=tuple(validated.plan.capability_cards),
        planned_nodes=validated.planned_nodes,
        executed_nodes=validated.executed_nodes,
        shadow_mode=validated.shadow_mode,
        adjustments=validated.adjustments,
    )
    logger.info(
        "planner_observability {}",
        json.dumps(
            {
                "turn_mode": payload.turn_mode,
                "capability_cards": list(payload.capability_cards),
                "planned_nodes": list(payload.planned_nodes),
                "executed_nodes": list(payload.executed_nodes),
                "shadow_mode": payload.shadow_mode,
                "adjustments": list(payload.adjustments),
            },
            ensure_ascii=False,
        ),
    )


def log_gate_observability(gate_chain: GateChainResult | None) -> None:
    if gate_chain is None:
        return
    veto = gate_chain.vetoed_by.id if gate_chain.vetoed_by else None
    logger.info(
        "gate_observability {}",
        json.dumps(
            {
                "allowed": gate_chain.allowed,
                "confidence_delta": gate_chain.confidence_delta,
                "vetoed_by": veto,
                "verdict_count": len(gate_chain.verdicts),
            },
            ensure_ascii=False,
        ),
    )


@contextmanager
def track_node_timing(node_id: str) -> Iterator[None]:
    started = time.perf_counter()
    status = "done"
    try:
        yield
    except Exception:
        status = "failed"
        raise
    finally:
        duration_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "evidence_node_timing {}",
            json.dumps(
                {"node_id": node_id, "duration_ms": duration_ms, "status": status},
                ensure_ascii=False,
            ),
        )
