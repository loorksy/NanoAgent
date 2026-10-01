#!/usr/bin/env bash
# One-page §11 closure readiness for Cloud Agent (cached quota; no live LLM by default).
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVENTS="$ROOT/section11-events"
RESULTS="$ROOT/section11-results-partial.json"
REQUIRE=13
LIVE_GATE=0

usage() {
  echo "Usage: $0 [--require-through N] [--live-gate] [EVENTS] [RESULTS]" >&2
  echo "  Default: cached quota + VPS env + blockers --skip-vps (no new LLM turn)." >&2
  echo "  --live-gate  also run mokli_upgrade_section11_blockers.sh (live quota probe on VPS)." >&2
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --require-through) REQUIRE="$2"; shift 2 ;;
    --live-gate) LIVE_GATE=1; shift ;;
    -h | --help) usage ;;
    --) shift; break ;;
    -*) echo "Unknown arg: $1" >&2; usage ;;
    *) break ;;
  esac
done
EVENTS="${1:-$EVENTS}"
RESULTS="${2:-$RESULTS}"

echo "== branch =="
git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo "unknown"

echo ""
echo "== OpenRouter reset =="
bash "$ROOT/scripts/mokli_upgrade_section11_wait_quota_reset.sh" 2>&1 || true

echo ""
echo "== cached quota (local JSONL) =="
bash "$ROOT/scripts/vps_section11_quota_status.sh" --local-dir "$EVENTS" || true

echo ""
echo "== VPS env (SSH) =="
bash "$ROOT/scripts/vps_section11_env_check.sh" 2>&1 \
  | grep -E '^(git_rev|git_branch|oanda_configured|llm_quota|gateway_model_preset|section11_model_override|agent_api_health|mokli_ui_http|mokli_pipe_show_diagnostics)=' \
  || bash "$ROOT/scripts/vps_section11_env_check.sh" || true

echo ""
echo "== §11 artifacts (require-through $REQUIRE; --skip-vps) =="
ARTIFACT_OK=0
if bash "$ROOT/scripts/mokli_upgrade_section11_blockers.sh" \
  --skip-vps --require-through "$REQUIRE" "$EVENTS" "$RESULTS"; then
  ARTIFACT_OK=1
fi

PROD_OK=0
if [[ "$LIVE_GATE" -eq 1 ]]; then
  echo ""
  echo "== production gate (live quota + OANDA + artifacts) =="
  if bash "$ROOT/scripts/mokli_upgrade_section11_blockers.sh" \
    --require-through "$REQUIRE" "$EVENTS" "$RESULTS"; then
    PROD_OK=1
  fi
else
  echo ""
  echo "HINT: live production gate — bash scripts/mokli_upgrade_section11_operator_unblock.sh --pull-vps"
fi

echo ""
echo "completion_status: artifact_ok=$ARTIFACT_OK production_ok=$PROD_OK require=$REQUIRE live_gate=$LIVE_GATE"
if [[ "$PROD_OK" -eq 1 ]]; then
  echo "SECTION11_COMPLETION_EXIT=0"
  exit 0
fi
if [[ "$ARTIFACT_OK" -eq 1 && "$REQUIRE" -le 10 ]]; then
  echo "SECTION11_COMPLETION_EXIT=0"
  exit 0
fi
echo "SECTION11_COMPLETION_EXIT=1" >&2
exit 1
