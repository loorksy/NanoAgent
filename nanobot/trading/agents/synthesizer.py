"""LLM final synthesizer — the only component that chooses buy/sell."""

from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable
from typing import Any

from nanobot.agent.tools.context import current_request_context
from nanobot.trading.agents.apply_model_decision import apply_model_decision
from nanobot.trading.agents.evidence import build_evidence_snapshot
from nanobot.trading.agents.synth_prompt import synth_system_prompt
from nanobot.trading.i18n import tr
from nanobot.trading.types import (
    AgentMarketContext,
    AgentRecommendation,
    EvidenceSnapshot,
    FinalDecisionResult,
    LiquidityResult,
    MultiTimeframeResult,
    NewsMacroResult,
    RiskAgentResult,
    StructureResult,
    SupplyDemandResult,
    VisualReview,
)

LLMComplete = Callable[[list[dict[str, Any]]], Awaitable[str]]

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)
_ARABIC_RE = re.compile(r"[\u0600-\u06FF]")


def _language_from_text(text: str) -> str:
    return "ar" if _ARABIC_RE.search(text or "") else "en"


def _extract_json(raw: str) -> dict[str, Any] | None:
    text = (raw or "").strip()
    if not text:
        return None
    match = _FENCE_RE.search(text)
    if match:
        text = match.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        payload = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


async def _runtime_complete(messages: list[dict[str, Any]]) -> str:
    ctx = current_request_context()
    runtime = ctx.runtime if ctx else None
    if runtime is None:
        return ""
    response = await runtime.provider.chat(
        messages=messages,
        model=runtime.model,
        max_tokens=min(getattr(runtime.generation, "max_tokens", 4096) or 4096, 4096),
        temperature=0.2,
    )
    return getattr(response, "content", None) or ""


def _browse_answer(
    verb: str,
    args: dict[str, Any],
    market: AgentMarketContext,
) -> dict[str, Any]:
    candles = market.candles
    if verb == "read_candles":
        count = int(args.get("count") or 40)
        rows = candles[-count:]
        return {
            "verb": verb,
            "candles": [
                {
                    "t": c.time_ms,
                    "o": c.open,
                    "h": c.high,
                    "l": c.low,
                    "c": c.close,
                }
                for c in rows
            ],
        }
    if verb == "read_zone":
        low = float(args.get("low") or 0)
        high = float(args.get("high") or 0)
        inside = sum(1 for c in candles if c.low <= high and c.high >= low)
        through = sum(1 for c in candles if c.close < low or c.close > high)
        return {"verb": verb, "touched": inside, "closedThrough": through, "bars": len(candles)}
    return {"verb": verb, "note": "Frame recapture is not available; use the numeric evidence."}


async def _call_model(
    *,
    snapshot: EvidenceSnapshot,
    language: str,
    complete: LLMComplete,
    market: AgentMarketContext,
    snapshots: list[dict[str, Any]],
) -> dict[str, Any] | None:
    system = synth_system_prompt(language)
    user_parts: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": "FROZEN EVIDENCE (do not invent prices outside evidenceLevels):\n"
            + json.dumps(snapshot.payload, ensure_ascii=False, default=str)[:18000],
        }
    ]
    for frame in snapshots[:4]:
        label = str(frame.get("timeframe") or "chart")
        user_parts.append({"type": "text", "text": f"CHART {label}: {frame.get('context') or ''}"})
        image = frame.get("image") or frame.get("dataUrl")
        if image:
            user_parts.append({"type": "image_url", "image_url": {"url": image}})

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_parts},
    ]
    raw = await complete(messages)
    parsed = _extract_json(raw)
    if parsed is None and raw:
        messages.append({"role": "assistant", "content": raw})
        messages.append(
            {
                "role": "user",
                "content": "Your previous reply was not valid JSON. Reply again with ONLY the JSON object.",
            }
        )
        parsed = _extract_json(await complete(messages))
    if parsed is None:
        return None

    browse = parsed.get("browse")
    for _ in range(2):
        if not isinstance(browse, dict) or not browse.get("verb"):
            break
        answer = _browse_answer(str(browse.get("verb")), browse, market)
        messages.append({"role": "assistant", "content": json.dumps(parsed, ensure_ascii=False)})
        messages.append(
            {
                "role": "user",
                "content": "BROWSE RESULT (re-issue the FULL decision JSON):\n"
                + json.dumps(answer, ensure_ascii=False),
            }
        )
        parsed = _extract_json(await complete(messages)) or parsed
        browse = parsed.get("browse") if isinstance(parsed, dict) else None
    return parsed


async def run_final_decision_synthesizer(
    risk: RiskAgentResult,
    structure: StructureResult,
    mtf: MultiTimeframeResult,
    news: NewsMacroResult,
    symbol: str = "XAUUSD",
    interval: str = "15m",
    *,
    market: AgentMarketContext | None = None,
    liquidity: LiquidityResult | None = None,
    supply_demand: SupplyDemandResult | None = None,
    geometry: dict[str, Any] | None = None,
    visual: VisualReview | None = None,
    visual_snapshots: list[dict[str, Any]] | None = None,
    team_briefing: str | None = None,
    spread: float | None = None,
    operator_text: str = "",
    issued_side: str | None = None,
    complete: LLMComplete | None = None,
) -> FinalDecisionResult:
    """LLM owns the side. Specialists and gates never choose buy/sell."""
    if market is None:
        return FinalDecisionResult(
            decision="wait",
            confidence=0.0,
            summary="Synthesizer missing market context.",
            key_reasons=["Operational blocker"],
            risk_warnings=[],
            recommendation=AgentRecommendation(action="wait", symbol=symbol, interval=interval),
            execution_state="blocked",
            refusal_summary="Market context missing",
        )

    from nanobot.trading.types import LiquidityResult, SupplyDemandResult

    snapshot = build_evidence_snapshot(
        market=market,
        structure=structure,
        liquidity=liquidity or LiquidityResult([], [], None, None, [], None),
        supply_demand=supply_demand or SupplyDemandResult([], None, None),
        mtf=mtf,
        news=news,
        risk=risk,
        geometry=geometry,
        visual=visual,
        team_briefing=team_briefing,
        spread=spread,
    )
    language = _language_from_text(operator_text)
    llm = complete or _runtime_complete
    try:
        parsed = await _call_model(
            snapshot=snapshot,
            language=language,
            complete=llm,
            market=market,
            snapshots=visual_snapshots or [],
        )
    except Exception as exc:
        return FinalDecisionResult(
            decision="wait",
            confidence=0.0,
            summary=f"Synthesizer unavailable: {exc}",
            key_reasons=["Operational blocker"],
            risk_warnings=[],
            recommendation=AgentRecommendation(action="wait", symbol=symbol, interval=interval),
            execution_state="blocked",
            refusal_summary=str(exc),
            visual_review=visual,
            evidence_snapshot=snapshot,
        )

    if parsed is None:
        return FinalDecisionResult(
            decision="wait",
            confidence=0.0,
            summary=tr("synth.no_usable_decision", language),
            key_reasons=[tr("synth.operational_blocker", language)],
            risk_warnings=[],
            recommendation=AgentRecommendation(action="wait", symbol=symbol, interval=interval),
            execution_state="blocked",
            refusal_summary=tr("synth.unavailable", language),
            visual_review=visual,
            evidence_snapshot=snapshot,
        )

    live = float(market.quote_mid or market.last_close)
    return apply_model_decision(
        parsed,
        snapshot=snapshot,
        live_price=live,
        atr=market.atr or 1.0,
        interval=interval,
        visual=visual,
        issued_side=issued_side if issued_side in ("buy", "sell") else None,
        locale=language,
    )
