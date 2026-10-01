"""Closed tool lists for desk roles.

Specialist lists stay outside ``SUBAGENT_FORBIDDEN_TOOLS``. The room lead and
the order clerk are not subagents, so their lists are enforced here instead of
by widening that set.
"""

from __future__ import annotations

from mokli.trading.policy_guard import MT5_EXECUTION_TOOLS, SUBAGENT_FORBIDDEN_TOOLS

_READ = frozenset({"fetch_evidence", "get_gold_quote", "read_file", "grep"})
_WEB = frozenset({"web_search", "web_fetch"})

ANALYST_TOOLS = _READ | _WEB
RISK_TOOLS = _READ
CHART_TOOLS = frozenset(
    {
        "capture_gold_chart",
        "get_gold_quote",
        "get_live_recommendation",
        "read_file",
        "grep",
    }
)
LAB_TOOLS = frozenset({"fast_backtest", "run_python", "read_file", "grep"})
LEAD_TOOLS = _READ | frozenset({"run_trading_team", "send_session_message"})
CLERK_TOOLS = _READ | frozenset({"mt5_propose_order"})
JOURNAL_TOOLS = frozenset({"read_file", "grep"})

IDLE_TOOLS = frozenset({"get_gold_quote", "fetch_evidence", "read_file", "grep"})

PROFILES: dict[str, frozenset[str]] = {
    "analyst": ANALYST_TOOLS,
    "risk": RISK_TOOLS,
    "chart": CHART_TOOLS,
    "lab": LAB_TOOLS,
    "lead": LEAD_TOOLS,
    "clerk": CLERK_TOOLS,
    "journal": JOURNAL_TOOLS,
}

_SPECIALIST_PROFILES = ("analyst", "risk", "chart", "lab")
for _name in _SPECIALIST_PROFILES:
    _overlap = PROFILES[_name] & SUBAGENT_FORBIDDEN_TOOLS
    if _overlap:
        raise RuntimeError(f"specialist profile {_name} overlaps forbidden tools: {_overlap}")

if PROFILES["clerk"] & MT5_EXECUTION_TOOLS != frozenset({"mt5_propose_order"}):
    raise RuntimeError("clerk execution surface must be propose only")
if "mt5_confirm_order" in PROFILES["clerk"]:
    raise RuntimeError("clerk must not confirm orders")


def profile_tools(profile: str) -> frozenset[str]:
    try:
        return PROFILES[profile]
    except KeyError as exc:
        raise KeyError(f"unknown desk profile {profile}") from exc
