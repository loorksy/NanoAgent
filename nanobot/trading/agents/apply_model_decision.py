"""Deterministic Lonora coercions after the model answers."""

from __future__ import annotations

import json
import re
from typing import Any

from nanobot.trading.cards.artifacts import parse_artifacts_requested
from nanobot.trading.i18n import tr
from nanobot.trading.types import (
    AgentRecommendation,
    Decision,
    DecisionHypothesis,
    DecisionTrace,
    EntryZone,
    EvidenceSnapshot,
    ExecutionState,
    FinalDecisionResult,
    PlanType,
    ScenarioWaypoint,
    TimeframeRoles,
    VisualReview,
)

GOLD_FOLLOW_THROUGH_POINTS = 12.5
# Max ±confidence from teamBriefing.macroDrivers consensus (documented rule).
MACRO_CONFIDENCE_WEIGHT = 0.12
_JSON_DIR = re.compile(r"^(buy|sell)$", re.I)


def parse_macro_drivers(snapshot: EvidenceSnapshot) -> list[dict[str, Any]]:
    """Read teamBriefing JSON (string or object) from the frozen evidence snapshot."""
    raw = (snapshot.payload or {}).get("teamBriefing") if snapshot else None
    if not raw:
        return []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return []
    if isinstance(raw, dict):
        drivers = raw.get("macroDrivers") or raw.get("macro_drivers") or []
    elif isinstance(raw, list):
        drivers = raw
    else:
        return []
    return [item for item in drivers if isinstance(item, dict)]


def macro_alignment_score(direction: Decision, drivers: list[dict[str, Any]]) -> float:
    """Signed consensus in [-1, 1]. Buy aligns with bullish; sell with bearish.

    Neutral and strength-0 drivers do not vote. Cache-hit (ran=false) still
    votes because the stored verdict is current evidence.
    """
    signed = 0.0
    weight = 0.0
    for item in drivers:
        bias = str(item.get("bias") or "").lower()
        try:
            strength = max(0, min(100, int(item.get("strength") or 0)))
        except (TypeError, ValueError):
            strength = 0
        if strength <= 0 or bias not in ("bullish", "bearish"):
            continue
        signed += (1.0 if bias == "bullish" else -1.0) * strength
        weight += strength
    if weight <= 0:
        return 0.0
    consensus = signed / weight
    if direction == "buy":
        return consensus
    if direction == "sell":
        return -consensus
    return 0.0


def apply_macro_confidence(confidence: float, alignment: float) -> float:
    """Add up to ±MACRO_CONFIDENCE_WEIGHT when macro consensus agrees or fights the side."""
    return max(0.05, min(0.95, confidence + MACRO_CONFIDENCE_WEIGHT * alignment))


def _round2(value: float) -> float:
    return round(float(value), 2)


def _clean_strings(values: Any, limit: int) -> list[str]:
    if not isinstance(values, list):
        return []
    out: list[str] = []
    for item in values:
        text = str(item).strip()[:240]
        if text:
            out.append(text)
        if len(out) >= limit:
            break
    return out


def infer_direction_from_evidence(snapshot: EvidenceSnapshot) -> Decision:
    mtf = (snapshot.payload.get("mtf") or {}) if snapshot else {}
    structure = (snapshot.payload.get("structure") or {}) if snapshot else {}
    bias = str(mtf.get("current_bias") or mtf.get("currentBias") or "")
    trend = str(structure.get("trend") or "")
    if bias == "bearish" or trend == "downtrend":
        return "sell"
    return "buy"


def grounded_price(value: Any, evidence_levels: list[float], *, atr: float) -> float | None:
    try:
        price = float(value)
    except (TypeError, ValueError):
        return None
    tolerance = max(atr * 0.15, 0.8)
    for level in evidence_levels:
        if abs(level - price) <= tolerance:
            return _round2(level)
    return None


def resolve_plan_levels(
    *,
    direction: Decision,
    parsed: dict[str, Any],
    snapshot: EvidenceSnapshot,
    atr: float,
) -> tuple[dict[str, Any] | None, str | None, str]:
    candidates = snapshot.payload.get("candidates") or []
    selected_id = parsed.get("selectedTradeCandidateId")
    selected = None
    if selected_id:
        selected = next(
            (
                c
                for c in candidates
                if str(c.get("id")) == str(selected_id) and c.get("action") == direction
            ),
            None,
        )
    if selected:
        targets = [float(t) for t in (selected.get("targets") or []) if t is not None]
        return (
            {
                "entry": float(selected["entry"]),
                "stop": float(selected["stopLoss"]),
                "targets": targets,
                "entryType": selected.get("entryType") or "market",
            },
            selected.get("id"),
            "candidate",
        )

    proposed = parsed.get("proposedLevels") or {}
    if not isinstance(proposed, dict):
        return None, None, "none"
    entry = grounded_price(proposed.get("entry"), snapshot.evidence_levels, atr=atr)
    stop = grounded_price(
        proposed.get("stopLoss") or proposed.get("stop_loss"),
        snapshot.evidence_levels,
        atr=atr,
    )
    raw_targets = proposed.get("targets") or []
    targets = [
        p
        for p in (grounded_price(t, snapshot.evidence_levels, atr=atr) for t in raw_targets)
        if p is not None
    ]
    if entry is None or stop is None or not targets:
        return None, None, "ungrounded"
    return {"entry": entry, "stop": stop, "targets": targets, "entryType": "limit_touch"}, None, "evidence_levels"


def apply_stop_buffer(direction: Decision, entry: float, stop: float, atr: float) -> float:
    buffer = max(atr * 0.35, 1.5)
    if direction == "buy":
        return _round2(min(stop, entry) - buffer) if stop >= entry else _round2(stop - buffer)
    return _round2(max(stop, entry) + buffer) if stop <= entry else _round2(stop + buffer)


def apply_stop_floor(direction: Decision, entry: float, stop: float, atr: float) -> float:
    floor = max(atr * 0.9, 4.0)
    distance = abs(entry - stop)
    if distance >= floor:
        return stop
    if direction == "buy":
        return _round2(entry - floor)
    return _round2(entry + floor)


def filter_targets(direction: Decision, entry: float, targets: list[float], atr: float) -> list[float]:
    min_span = max(atr * 0.6, 3.0)
    cleaned: list[float] = []
    for target in targets:
        if direction == "buy" and target <= entry:
            continue
        if direction == "sell" and target >= entry:
            continue
        if cleaned and abs(target - cleaned[-1]) < min_span * 0.35:
            continue
        cleaned.append(_round2(target))
        if len(cleaned) >= 3:
            break
    if len(cleaned) < 2:
        step = max(atr * 2.0, 8.0)
        first = cleaned[0] if cleaned else (_round2(entry + step) if direction == "buy" else _round2(entry - step))
        second = _round2(first + step) if direction == "buy" else _round2(first - step)
        cleaned = [first, second]
    return cleaned[:3]


def entry_print_state(
    *,
    direction: Decision,
    entry: float,
    live: float,
) -> str | None:
    """Return 'through', 'approach', or None."""
    if direction == "sell":
        if live < entry:
            return "through"
        if 0 <= live - entry <= GOLD_FOLLOW_THROUGH_POINTS:
            return "approach"
        return None
    if live > entry:
        return "through"
    if 0 <= entry - live <= GOLD_FOLLOW_THROUGH_POINTS:
        return "approach"
    return None


def pin_scenario_path(
    waypoints: Any,
    *,
    last_price: float,
    start: float,
    min_points: int,
    max_points: int,
) -> list[ScenarioWaypoint]:
    rows: list[ScenarioWaypoint] = []
    if isinstance(waypoints, list):
        for item in waypoints:
            if not isinstance(item, dict):
                continue
            try:
                bars = int(item.get("barsAhead") or item.get("bars_ahead") or 0)
                price = float(item.get("price"))
            except (TypeError, ValueError):
                continue
            if bars <= 0:
                continue
            rows.append(ScenarioWaypoint(bars_ahead=bars, price=_round2(price), label=str(item.get("label") or "")))
    rows.sort(key=lambda w: w.bars_ahead)
    unique: list[ScenarioWaypoint] = []
    seen_bars: set[int] = set()
    for row in rows:
        if row.bars_ahead in seen_bars:
            continue
        seen_bars.add(row.bars_ahead)
        unique.append(row)
        if len(unique) >= max_points:
            break
    if not unique:
        unique = [
            ScenarioWaypoint(bars_ahead=2, price=_round2((start + last_price) / 2), label="pullback"),
            ScenarioWaypoint(bars_ahead=6, price=_round2(last_price), label="target"),
        ]
    if unique[-1].price != _round2(last_price):
        unique[-1] = ScenarioWaypoint(
            bars_ahead=unique[-1].bars_ahead,
            price=_round2(last_price),
            label=unique[-1].label or "final",
        )
    if len(unique) < min_points:
        mid = _round2((start + last_price) / 2)
        unique.insert(0, ScenarioWaypoint(bars_ahead=1, price=mid, label="impulse"))
    # Never a straight line: ensure a mid waypoint differs from the chord.
    if len(unique) == 2:
        mid = _round2((start + last_price) / 2)
        unique.insert(1, ScenarioWaypoint(bars_ahead=max(unique[0].bars_ahead + 1, 3), price=mid, label="pullback"))
        if unique[1].bars_ahead >= unique[2].bars_ahead:
            unique[2] = ScenarioWaypoint(
                bars_ahead=unique[1].bars_ahead + 2,
                price=unique[2].price,
                label=unique[2].label,
            )
    return unique[:max_points]


def apply_revision(
    current_side: Decision,
    parsed_direction: Decision,
) -> Decision:
    """Reevaluation may revise same-side levels only."""
    if parsed_direction != current_side:
        return current_side
    return parsed_direction


def apply_model_decision(
    parsed: dict[str, Any],
    *,
    snapshot: EvidenceSnapshot,
    live_price: float,
    atr: float,
    interval: str = "15m",
    visual: VisualReview | None = None,
    issued_side: Decision | None = None,
    locale: str = "ar",
) -> FinalDecisionResult:
    raw_dir = str(parsed.get("direction") or "").lower()
    direction: Decision = raw_dir if _JSON_DIR.match(raw_dir) else infer_direction_from_evidence(snapshot)
    if issued_side in ("buy", "sell"):
        direction = apply_revision(issued_side, direction)

    raw_plan = str(parsed.get("planType") or parsed.get("plan_type") or "immediate").lower()
    plan_type: PlanType = raw_plan if raw_plan in ("immediate", "anticipatory", "conditional") else "immediate"

    levels, selected_id, source = resolve_plan_levels(
        direction=direction, parsed=parsed, snapshot=snapshot, atr=atr
    )
    warnings = _clean_strings(parsed.get("riskWarnings") or parsed.get("risk_warnings"), 6)
    if levels is None:
        if source == "ungrounded":
            warnings.insert(0, tr("warning.ungrounded_levels", locale))
        # Fall back to first same-direction candidate so a successful analysis still ships a plan.
        fallback = next(
            (
                c
                for c in (snapshot.payload.get("candidates") or [])
                if c.get("action") == direction
            ),
            None,
        )
        if fallback:
            levels = {
                "entry": float(fallback["entry"]),
                "stop": float(fallback["stopLoss"]),
                "targets": [float(t) for t in (fallback.get("targets") or [])],
                "entryType": fallback.get("entryType") or "market",
            }
            selected_id = fallback.get("id")
            source = "candidate_fallback"

    if levels:
        entry = _round2(levels["entry"])
        stop = apply_stop_floor(
            direction,
            entry,
            apply_stop_buffer(direction, entry, float(levels["stop"]), atr),
            atr,
        )
        targets = filter_targets(direction, entry, list(levels.get("targets") or []), atr)
        levels = {**levels, "entry": entry, "stop": stop, "targets": targets}

    mtf = snapshot.payload.get("mtf") or {}
    mtf_conflict = bool(mtf.get("conflict"))
    competing = {
        str(c.get("action"))
        for c in (snapshot.payload.get("candidates") or [])
        if c.get("action") in ("buy", "sell")
    }
    coerced_from_immediate = False
    if plan_type == "immediate" and (mtf_conflict or len(competing) > 1):
        plan_type = "conditional"
        coerced_from_immediate = True
        warnings.insert(0, tr("warning.mtf_conflict", locale))

    activation_rule = parsed.get("activationRule") or parsed.get("activation_rule")
    activation_condition = parsed.get("activationCondition") or parsed.get("activation_condition")
    if plan_type == "immediate":
        activation_rule = None
        activation_condition = None
    elif coerced_from_immediate and levels and not activation_rule:
        activation_rule = {
            "kind": "candle_close_below" if direction == "sell" else "candle_close_above",
            "level": levels["entry"],
            "timeframe": interval,
        }
        activation_condition = activation_condition or (
            f"Close {'below' if direction == 'sell' else 'above'} {levels['entry']}"
        )

    print_anchor_ms: int | None = None
    if levels and plan_type != "immediate" and live_price > 0:
        printed = entry_print_state(direction=direction, entry=float(levels["entry"]), live=live_price)
        if printed:
            keep_approach = printed == "approach" and coerced_from_immediate
            if not keep_approach:
                written = float(levels["entry"])
                live = _round2(live_price)
                stop = float(levels["stop"])
                would_breach = live >= stop if direction == "sell" else live <= stop
                if not would_breach:
                    fill_at = written if printed == "through" and abs(live - written) <= GOLD_FOLLOW_THROUGH_POINTS else live
                    if printed == "through" and abs(live - written) <= max(atr * 0.25, 2.0):
                        fill_at = written
                    next_targets = filter_targets(direction, fill_at, list(levels["targets"]), atr)
                    if next_targets:
                        levels = {
                            **levels,
                            "entry": _round2(fill_at),
                            "targets": next_targets,
                            "entryType": "market",
                        }
                        plan_type = "immediate"
                        activation_rule = None
                        activation_condition = None
                        warnings.insert(0, tr("warning.activation_printed", locale))

    execution_state: ExecutionState = "valid_now" if plan_type == "immediate" else "awaiting_activation"
    roles_raw = parsed.get("timeframeRoles") or parsed.get("timeframe_roles") or {}
    roles = TimeframeRoles(
        lead=str(roles_raw.get("lead") or interval),
        context=str(roles_raw.get("context") or "4h"),
        timing=str(roles_raw.get("timing") or "5m"),
    )
    trace_raw = parsed.get("decisionTrace") or parsed.get("decision_trace") or {}
    hyps = []
    for item in trace_raw.get("hypotheses") or []:
        if isinstance(item, dict) and item.get("scenario"):
            hyps.append(
                DecisionHypothesis(
                    scenario=str(item["scenario"]),
                    supporting=_clean_strings(item.get("supporting"), 4),
                    opposing=_clean_strings(item.get("opposing"), 4),
                )
            )
    trace = DecisionTrace(
        hypotheses=hyps,
        chosen_because=str(trace_raw.get("chosenBecause") or trace_raw.get("chosen_because") or "")[:400],
        plan_type_because=str(trace_raw.get("planTypeBecause") or trace_raw.get("plan_type_because") or "")[:400],
    )

    rec = AgentRecommendation(action=direction, symbol="XAUUSD", interval=interval)
    if levels:
        entry = float(levels["entry"])
        stop = float(levels["stop"])
        targets = list(levels["targets"])
        risk = abs(entry - stop)
        reward = abs(targets[0] - entry) if targets else 0.0
        rec = AgentRecommendation(
            action=direction,
            plan_type=plan_type,
            execution_state=execution_state,
            entry=entry,
            entry_type="market" if plan_type == "immediate" else str(levels.get("entryType") or "limit_touch"),
            entry_zone=EntryZone(low=min(entry, live_price or entry), high=max(entry, live_price or entry)),
            stop_loss=stop,
            targets=targets,
            take_profit=targets[0],
            activation_condition=str(activation_condition) if activation_condition else None,
            activation_rule=activation_rule if isinstance(activation_rule, dict) else None,
            invalidation_rule=str(parsed.get("invalidationRule") or parsed.get("invalidation_rule") or "")[:400] or None,
            invalidation_level=stop,
            alternative_scenario=str(parsed.get("alternativeScenario") or "")[:400] or None,
            validity_candles=int(parsed.get("validityCandles") or 12),
            timeframe_roles=roles,
            decision_trace=trace,
            scenario_path=pin_scenario_path(
                parsed.get("scenarioPath"),
                last_price=targets[-1],
                start=live_price or entry,
                min_points=2,
                max_points=6,
            ),
            alternative_scenario_path=pin_scenario_path(
                parsed.get("alternativeScenarioPath"),
                last_price=stop,
                start=live_price or entry,
                min_points=2,
                max_points=4,
            ),
            rr=(reward / risk) if risk else None,
            net_rr=(reward / risk) if risk else None,
            anchor_time=print_anchor_ms,
            symbol="XAUUSD",
            interval=interval,
        )

    confidence = parsed.get("confidence")
    try:
        conf = max(0.05, min(0.95, float(confidence)))
    except (TypeError, ValueError):
        conf = 0.55

    # Documented rule: teamBriefing.macroDrivers adjust confidence after the model
    # answers. Specialists still never flip the side.
    reasons = _clean_strings(parsed.get("keyReasons") or parsed.get("key_reasons"), 6)
    drivers = parse_macro_drivers(snapshot)
    alignment = macro_alignment_score(direction, drivers)
    if drivers and abs(alignment) > 1e-9:
        before = conf
        conf = apply_macro_confidence(conf, alignment)
        if abs(conf - before) >= 0.01:
            voted = sum(
                1
                for item in drivers
                if str(item.get("bias") or "").lower() in ("bullish", "bearish")
            )
            note = (
                f"Macro drivers {alignment:+.2f} alignment ({voted} voted) "
                f"→ confidence {before:.2f}→{conf:.2f}"
            )
            reasons = [*reasons[:5], note]

    artifacts_requested = parse_artifacts_requested(
        parsed.get("artifactsRequested") or parsed.get("artifacts_requested")
    )

    return FinalDecisionResult(
        decision=direction,
        confidence=conf,
        summary=str(parsed.get("summary") or f"Gold {direction.upper()}")[:900],
        key_reasons=reasons[:6],
        risk_warnings=warnings,
        recommendation=rec,
        plan_type=plan_type,
        execution_state=execution_state,
        public_reasoning_summary=_clean_strings(
            parsed.get("publicReasoningSummary") or parsed.get("public_reasoning_summary"), 4
        ),
        visual_review=visual,
        evidence_snapshot=snapshot,
        artifacts_requested=artifacts_requested,
    )
