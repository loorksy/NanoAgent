#!/usr/bin/env bash
# Cloud Agent / workstation snapshot: VPS quota probe + local §11 blockers (no LLM, no pull).
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/section11_quota_hints.sh
source "$ROOT/scripts/section11_quota_hints.sh"
EVENTS="$ROOT/section11-events"
RESULTS="$ROOT/section11-results-partial.json"
PYTHON="${ROOT}/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON=python3
fi
REQUIRE=13

while [[ $# -gt 0 ]]; do
  case "$1" in
    --require-through) REQUIRE="$2"; shift 2 ;;
    -h | --help)
      echo "Usage: $0 [--require-through N]" >&2
      exit 0
      ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

VPS_BRANCH="${MOKLI_SECTION11_VPS_BRANCH:-cursor/section11-vps-rows-d9e1}"
section11_print_cloud_vps_rev "$ROOT" "$VPS_BRANCH"
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
echo "== VPS LLM quota (cached probe; no new LLM call) =="
QUOTA_OK=0
if bash "$ROOT/scripts/vps_section11_quota_status.sh"; then
  QUOTA_OK=1
else
  echo "HINT: live probe: bash scripts/vps_section11_quota_probe.sh" >&2
  echo "HINT: after reset: bash scripts/mokli_upgrade_section11_timer_wake.sh --wait-quota" >&2
  echo "HINT: or: bash scripts/mokli_upgrade_section11_post_quota.sh --wait --pull-vps" >&2
fi

echo ""
echo "== VPS env snapshot (SSH; no live LLM turn) =="
if vps_ssh_ready; then
  install="${MOKLI_INSTALL_DIR:-/opt/nanoagent}"
  vps_ssh "cd $(printf '%q' "$install") && bash scripts/vps_section11_env_check.sh" 2>&1 \
    | grep -E '^(git_rev|git_branch|agent_api_health|oanda_configured|oanda_env_file|mokli_ui_http|mokli_pipe_show_diagnostics|gateway_model_preset|section11_model_override)=' \
    || echo "WARN: vps_section11_env_check failed" >&2
else
  echo "SKIP: set MOKLI_SSH_HOST or VPS+VPSPASS for VPS snapshot" >&2
fi

echo ""
echo "== live rerun rows (after quota) =="
if [[ -d "$EVENTS" ]]; then
  section11_prune_row5_stale_no_nested "$EVENTS" "$ROOT"
fi
RERUN_ROWS=$("$PYTHON" "$ROOT/scripts/mokli_upgrade_section11_validate.py" \
  --dir "$EVENTS" --require-through "$REQUIRE" --print-live-rerun-rows 2>/dev/null || true)
echo "live_rerun_rows=${RERUN_ROWS:-none}"

echo ""
echo "== Local §11 artifacts (--skip-vps) =="
BLOCK_OK=0
CLOSURE_ERRORS=""
set +e
BLOCK_COMBINED=$(
  bash "$ROOT/scripts/mokli_upgrade_section11_blockers.sh" \
    --skip-vps --require-through "$REQUIRE" 2>&1
)
BLOCK_EC=$?
set -e
printf '%s\n' "$BLOCK_COMBINED"
if [[ "$BLOCK_EC" -eq 0 ]]; then
  BLOCK_OK=1
else
  CLOSURE_ERRORS=$(printf '%s\n' "$BLOCK_COMBINED" | sed -n 's/^closure_errors=\([0-9]*\).*/\1/p' | tail -1)
fi

ALLOW_PARTIAL_CE=""
if [[ "$REQUIRE" -ge 13 && -d "$EVENTS" && -f "$RESULTS" ]]; then
  ALLOW_PARTIAL_CE=$(
    section11_allow_partial_closure_errors \
      "$PYTHON" "$ROOT/scripts/mokli_upgrade_section11_validate.py" \
      "$EVENTS" "$RESULTS" "$REQUIRE"
  )
fi

PARTIAL10_OK=0
PARTIAL10_GATE=0
if [[ "$REQUIRE" -gt 10 && "$BLOCK_OK" -eq 0 ]]; then
  echo ""
  echo "== Local §11 partial pack (require-through 10) =="
  if bash "$ROOT/scripts/mokli_upgrade_section11_blockers.sh" \
    --skip-vps --require-through 10; then
    PARTIAL10_OK=1
    echo ""
    echo "== production gate @10 (skip quota/OANDA/pull) =="
    if bash "$ROOT/scripts/mokli_upgrade_section11_production_gate.sh" \
      --skip-quota --skip-oanda --skip-pull --require-through 10; then
      PARTIAL10_GATE=1
    fi
  fi
fi

echo ""
WAKE_UTC_FIELD="wake_after_buffer_utc=unknown"
[[ -n "${WAKE_UTC:-}" ]] && WAKE_UTC_FIELD="wake_after_buffer_utc=$WAKE_UTC"
echo "cloud_status: quota_ok=$QUOTA_OK blockers_ok=$BLOCK_OK partial10_ok=$PARTIAL10_OK partial10_gate=$PARTIAL10_GATE require_through=$REQUIRE closure_errors=${CLOSURE_ERRORS:-0} allow_partial_closure_errors=${ALLOW_PARTIAL_CE:-unknown} live_rerun_rows=${RERUN_ROWS:-none} seconds_until_reset=$RESET_SEC $WAKE_UTC_FIELD"
if [[ "$PARTIAL10_OK" -eq 1 && "$REQUIRE" -gt 10 ]]; then
  echo "HINT: artifact pack 1–10 OK — bash $0 --require-through 10" >&2
fi
if [[ "$QUOTA_OK" -eq 1 && "$BLOCK_OK" -eq 1 ]]; then
  echo "READY for section11_close.sh --apply --require-through $REQUIRE --results section11-results-partial.json"
  exit 0
fi
if [[ "$BLOCK_OK" -eq 1 && "$REQUIRE" -le 10 ]]; then
  echo "OK §11 artifacts through row $REQUIRE (quota_ok=$QUOTA_OK — not production closure)"
  exit 0
fi
exit 1
