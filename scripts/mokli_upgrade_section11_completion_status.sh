#!/usr/bin/env bash
# One-page §11 closure readiness for Cloud Agent (cached quota; no live LLM by default).
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/section11_quota_hints.sh
source "$ROOT/scripts/section11_quota_hints.sh"
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

PYTHON="${ROOT}/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON=python3
fi

echo "== branch =="
git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo "unknown"

echo ""
echo "== live rerun rows (validate --print-live-rerun-rows) =="
RERUN_ROWS=$("$PYTHON" "$ROOT/scripts/mokli_upgrade_section11_validate.py" \
  --dir "$EVENTS" --require-through "$REQUIRE" --print-live-rerun-rows 2>/dev/null || true)
echo "live_rerun_rows=${RERUN_ROWS:-none}"

echo ""
echo "== OpenRouter reset =="
RESET_SEC="unknown"
RESET_OUT=$(bash "$ROOT/scripts/mokli_upgrade_section11_wait_quota_reset.sh" 2>&1 || true)
printf '%s\n' "$RESET_OUT"
WAKE_BUFFER_OUT=$(section11_emit_wake_after_buffer "$RESET_OUT")
if [[ -n "$WAKE_BUFFER_OUT" ]]; then
  printf '%s\n' "$WAKE_BUFFER_OUT"
fi
WAKE_UTC=$(printf '%s\n' "$WAKE_BUFFER_OUT" | sed -n 's/^wake_after_buffer_utc=\(.*\)/\1/p' | tail -1)
parsed=$(printf '%s\n' "$RESET_OUT" | sed -n 's/^seconds_until_reset=\([^ ]*\).*/\1/p' | tail -1)
[[ -n "$parsed" ]] && RESET_SEC="$parsed"

echo ""
echo "== cached quota (local JSONL) =="
bash "$ROOT/scripts/vps_section11_quota_status.sh" --local-dir "$EVENTS" || true

echo ""
echo "== VPS env (SSH) =="
bash "$ROOT/scripts/vps_section11_env_check.sh" 2>&1 \
  | grep -E '^(git_rev|git_branch|oanda_configured|oanda_env_file|llm_quota|gateway_model_preset|section11_model_override|agent_api_health|mokli_ui_http|mokli_pipe_show_diagnostics)=' \
  || bash "$ROOT/scripts/vps_section11_env_check.sh" || true

echo ""
echo "== §11 artifacts (require-through $REQUIRE; --skip-vps) =="
ARTIFACT_OK=0
CLOSURE_ERRORS=""
set +e
BLOCK_COMBINED=$(
  bash "$ROOT/scripts/mokli_upgrade_section11_blockers.sh" \
    --skip-vps --require-through "$REQUIRE" "$EVENTS" "$RESULTS" 2>&1
)
BLOCK_EC=$?
set -e
printf '%s\n' "$BLOCK_COMBINED"
if [[ "$BLOCK_EC" -eq 0 ]]; then
  ARTIFACT_OK=1
else
  CLOSURE_ERRORS=$(printf '%s\n' "$BLOCK_COMBINED" | sed -n 's/^closure_errors=\([0-9]*\).*/\1/p' | tail -1)
fi

ALLOW_PARTIAL_CE=""
if [[ "$REQUIRE" -ge 13 && -d "$EVENTS" && -f "$RESULTS" ]]; then
  set +e
  ALLOW_PARTIAL_CE=$(
    "$PYTHON" "$ROOT/scripts/mokli_upgrade_section11_validate.py" \
      --dir "$EVENTS" --results "$RESULTS" --require-through "$REQUIRE" --allow-partial 2>&1 \
      | sed -n 's/^closure_errors=\([0-9]*\).*/\1/p' | tail -1
  )
  set -e
fi

PARTIAL10_OK=0
PARTIAL10_GATE=0
if [[ "$REQUIRE" -gt 10 ]]; then
  echo ""
  echo "== §11 partial pack (require-through 10; --skip-vps) =="
  if bash "$ROOT/scripts/mokli_upgrade_section11_blockers.sh" \
    --skip-vps --require-through 10 "$EVENTS" "$RESULTS"; then
    PARTIAL10_OK=1
    echo ""
    echo "== production gate @10 (skip quota/OANDA/pull) =="
    if bash "$ROOT/scripts/mokli_upgrade_section11_production_gate.sh" \
      --skip-quota --skip-oanda --skip-pull --require-through 10; then
      PARTIAL10_GATE=1
    fi
  fi
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
WAKE_UTC_FIELD="wake_after_buffer_utc=unknown"
[[ -n "${WAKE_UTC:-}" ]] && WAKE_UTC_FIELD="wake_after_buffer_utc=$WAKE_UTC"
echo "completion_status: artifact_ok=$ARTIFACT_OK partial10_ok=$PARTIAL10_OK partial10_gate=$PARTIAL10_GATE production_ok=$PROD_OK require=$REQUIRE live_gate=$LIVE_GATE closure_errors=${CLOSURE_ERRORS:-0} allow_partial_closure_errors=${ALLOW_PARTIAL_CE:-unknown} live_rerun_rows=${RERUN_ROWS:-none} seconds_until_reset=$RESET_SEC $WAKE_UTC_FIELD"
if [[ "$PROD_OK" -eq 1 ]]; then
  echo "SECTION11_COMPLETION_EXIT=0"
  exit 0
fi
if [[ "$ARTIFACT_OK" -eq 1 && "$REQUIRE" -le 10 ]]; then
  echo "SECTION11_COMPLETION_EXIT=0"
  exit 0
fi
if [[ "$REQUIRE" -gt 10 && "$PARTIAL10_OK" -eq 0 ]]; then
  echo "HINT: sync partial JSONL 1–10 — bash scripts/mokli_upgrade_section11_sync_from_vps.sh --pull-vps" >&2
fi
echo "SECTION11_COMPLETION_EXIT=1" >&2
exit 1
