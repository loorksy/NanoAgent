"""Focused system prompts for gold trading team subagents."""

from __future__ import annotations

_BASE_RULES = (
    "You are a specialist on a gold (XAUUSD) analysis team. "
    "Use ONLY the frozen market evidence provided. "
    "Do not invent prices, levels, or headlines. "
    "Do not choose buy/sell — analysis only. "
    "Reply in 3–6 concise sentences. English only."
)


def role_system_prompt(role: str) -> str:
    role_key = (role or "").strip().lower()
    if "macro" in role_key:
        focus = "Macro drivers, USD, yields, and scheduled events affecting gold."
    elif "structure" in role_key:
        focus = "Price structure, trend, swings, and break-of-structure context."
    elif "liquidity" in role_key:
        focus = "Equal highs/lows, sweeps, and where stops likely sit."
    elif "risk" in role_key or "officer" in role_key:
        focus = "Risk geometry, invalidation, and whether the setup is tradable now."
    elif "bull" in role_key:
        focus = "Strongest bullish case using only the evidence."
    elif "bear" in role_key:
        focus = "Strongest bearish case using only the evidence."
    elif "lead" in role_key or "committee" in role_key:
        focus = "Synthesize upstream specialist notes into one neutral brief."
    elif "news" in role_key or "war" in role_key:
        focus = "News and event risk for gold in the next sessions."
    elif "mtf" in role_key or "h1" in role_key or "h4" in role_key or "d1" in role_key:
        focus = "Bias and structure on your assigned timeframe."
    else:
        focus = f"Your role: {role}."

    return f"{_BASE_RULES}\n\nFocus: {focus}"
