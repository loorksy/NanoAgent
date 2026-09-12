"""Final decision synthesizer — rule-based pick of best candidate."""

from __future__ import annotations

from nanobot.trading.types import (
    AgentRecommendation,
    FinalDecisionResult,
    MultiTimeframeResult,
    NewsMacroResult,
    RiskAgentResult,
    StructureResult,
)


def run_final_decision_synthesizer(
    risk: RiskAgentResult,
    structure: StructureResult,
    mtf: MultiTimeframeResult,
    news: NewsMacroResult,
    symbol: str = "XAUUSD",
    interval: str = "15m",
) -> FinalDecisionResult:
    cand = risk.selected_candidate
    if cand is None or cand.action == "wait" or not risk.validation.accepted:
        return FinalDecisionResult(
            decision="wait",
            confidence=0.3,
            summary="No tradable setup after risk filtering.",
            key_reasons=["Risk agent rejected candidates"],
            risk_warnings=risk.validation.reasons,
            recommendation=AgentRecommendation(action="wait", symbol=symbol, interval=interval),
            plan_type=None,
            execution_state="blocked",
            public_reasoning_summary=["Waiting for clearer structure"],
        )

    confidence = min(0.95, 0.5 + cand.quality_score * 0.4)
    if mtf.conflict:
        confidence -= 0.1
    if news.news_risk == "high":
        confidence -= 0.1

    reasons = [
        f"Structure trend: {structure.trend}",
        f"MTF bias: {mtf.current_bias} (HTF {mtf.higher_bias})",
        f"Setup: {cand.setup_type} R:R {cand.rr:.2f}",
    ]
    warnings: list[str] = []
    if mtf.conflict:
        warnings.append("Higher timeframe conflicts with entry timeframe")
    if news.news_risk == "high":
        warnings.append("Elevated news risk")

    rec = AgentRecommendation(
        action=cand.action,
        plan_type="immediate",
        execution_state="valid_now",
        entry=cand.entry,
        entry_type=cand.entry_type,
        stop_loss=cand.stop_loss,
        targets=cand.targets,
        anchor_time=None,
        symbol=symbol,
        interval=interval,
    )
    return FinalDecisionResult(
        decision=cand.action,
        confidence=max(0.1, confidence),
        summary=f"Gold {cand.action.upper()} from {cand.setup_type} with R:R {cand.rr:.2f}",
        key_reasons=reasons,
        risk_warnings=warnings,
        recommendation=rec,
        plan_type="immediate",
        execution_state="valid_now",
        public_reasoning_summary=reasons[:3],
    )
