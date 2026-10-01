#!/usr/bin/env bash
# Operator runbook for §11 rows 11–13 (after quota + OANDA). Does not call LLM or UI.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cat <<EOF
§11 rows 11–13 — run in order after:
  bash scripts/vps_section11_env_check.sh --require-quota --require-oanda
  bash scripts/vps_section11_row1_after_p0.sh   # optional P0 live delta

Row 3 (multi-tool, if row 3 still PARTIAL):
  bash scripts/vps_section11_row3_multi_tool.sh
  → 03-multi-tool-v2.jsonl; expect tools>=2 in diagnostic extract

Row 5 (spawn/subagents, if nested_rounds=0 / spawn 429):
  bash scripts/vps_section11_row5_subagents.sh
  → 05-subagents-v2.jsonl; expect nested_rounds>=1 in diagnostic

Row 9 (long session, if quota_blocked_likely in session-summary):
  bash scripts/vps_section11_row9_long_session.sh
  → 09-long-session-v3.jsonl; then extract --session-summary on that file

Row 10 (backtest, if market_feed_unconfigured):
  bash scripts/vps_section11_row10_backtest.sh
  → 10-backtest-v2.jsonl

Row 11 (paper, Agent API + OANDA candles):
  bash scripts/vps_section11_row11_paper.sh
  → section11-events/11-paper.jsonl on VPS; JSONL must include paper/run_state (validate @13)

Row 12 (desktop UI + Mokli pipe, not raw Agent API):
  bash scripts/local_section11_row12_smoke.sh     # dev pre-check
  bash scripts/vps_section11_row12_desktop.sh     # VPS UI/API/pipe check
  Chat via Open WebUI Mokli pipe with SHOW_DIAGNOSTICS; save JSONL as 12-desktop-ui.jsonl
  → must include structured/decision events + diagnostic in>0 (validate @13)

Row 13 (mobile / SDK — production needs device JSONL):
  bash scripts/mokli_upgrade_section11_row13_ci.sh  # CI proxy only (does NOT satisfy validate @13)
  bash scripts/vps_section11_row13_mobile.sh
  Device session → section11-events/13-mobile.jsonl (tool/status/structured events, not diagnostic-only)

Close:
  bash scripts/mokli_upgrade_section11_production_gate.sh --pull-vps
  bash scripts/mokli_upgrade_section11_close.sh --apply --require-through 13 --results section11-results-partial.json

Docs: docs/mokli-agent-upgrade-operator-handoff.md
EOF
