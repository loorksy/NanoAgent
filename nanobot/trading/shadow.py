"""Shadow comparison logs for the unified loop. Never stores recommendations."""

from __future__ import annotations

import json
import random
from typing import Any

from loguru import logger

from nanobot.trading.config import load_trading_config
from nanobot.trading.turn_planner import plan_turn
from nanobot.trading.turn_session import current_turn_session


def should_sample_dual_run() -> bool:
    config = load_trading_config()
    if config.unified_loop_mode != "shadow":
        return False
    sample = config.unified_loop_shadow_sample
    if sample <= 0:
        return False
    if sample >= 100:
        return True
    return random.random() * 100 < sample


def log_regex_counterfactual(
    message: str,
    *,
    active_recommendation_live: bool = False,
    extra: dict[str, Any] | None = None,
) -> None:
    """Always-on cheap log: what plan_turn would have said vs tools actually used."""
    config = load_trading_config()
    if config.unified_loop_mode == "off":
        return
    turn_plan = plan_turn(message, active_recommendation_live=active_recommendation_live)
    session = current_turn_session()
    payload = {
        "unified_loop_mode": config.unified_loop_mode,
        "old_mode": turn_plan.mode,
        "old_intent": turn_plan.intent.kind,
        "old_nodes": list(turn_plan.nodes),
        "new_tools": list(session.tools_called) if session else [],
        "new_nodes": list(session.nodes_fetched) if session else [],
        "new_kernel": bool(session.kernel_ran) if session else False,
        "new_decision": session.kernel_decision if session else None,
        "new_would_store": False,
        **(extra or {}),
    }
    logger.info("unified_loop_shadow {}", json.dumps(payload, ensure_ascii=False, default=str))


def log_shadow_comparison(payload: dict[str, Any]) -> None:
    logger.info("unified_loop_shadow {}", json.dumps(payload, ensure_ascii=False, default=str))


def maybe_mark_dual_run_sample() -> None:
    """Log sampled dual-run eligibility. Never blocks the serving path."""
    if not should_sample_dual_run():
        return
    log_shadow_comparison(
        {
            "event": "dual_run_sampled",
            "new_would_store": False,
            "note": "CI replay harness is the deterministic dual-run; live LLM clone is optional",
        }
    )


def replay_divergence(
    *,
    old_decision: str | None,
    new_decision: str | None,
    old_kernel: bool,
    new_kernel: bool,
    old_nodes: list[str] | None = None,
    new_nodes: list[str] | None = None,
) -> list[str]:
    flags: list[str] = []
    if bool(old_kernel) != bool(new_kernel):
        flags.append("kernel_mismatch")
    if (old_decision or "none") != (new_decision or "none"):
        flags.append("side_mismatch")
    if old_nodes is not None and new_nodes is not None and set(old_nodes) != set(new_nodes):
        flags.append("node_set_mismatch")
    return flags
