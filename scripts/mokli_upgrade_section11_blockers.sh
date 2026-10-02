#!/usr/bin/env bash
# One-page §11 production blockers: VPS env + validate through 13 (exit 1 if not closable).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/section11_quota_hints.sh
source "$ROOT/scripts/section11_quota_hints.sh"
PYTHON="${ROOT}/.venv/bin/python"
[[ -x "$PYTHON" ]] || PYTHON=python3
SKIP_VPS=0
REQUIRE=13
EVENTS="$ROOT/section11-events"
RESULTS="$ROOT/section11-results-partial.json"

usage() {
  echo "Usage: $0 [--skip-vps] [--require-through N] [EVENTS_DIR] [RESULTS_JSON]" >&2
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-vps) SKIP_VPS=1; shift ;;
    --require-through) REQUIRE="$2"; shift 2 ;;
    -h | --help) usage ;;
    --*) echo "Unknown flag: $1" >&2; usage ;;
    *) break ;;
  esac
done
EVENTS="${1:-$EVENTS}"
RESULTS="${2:-$RESULTS}"
if [[ $# -gt 2 ]]; then
  usage
fi

RERUN_ROWS=$("$PYTHON" "$ROOT/scripts/mokli_upgrade_section11_validate.py" \
  --dir "$EVENTS" --require-through "$REQUIRE" --print-live-rerun-rows 2>/dev/null || true)

RESET_SEC="unknown"
RESET_OUT=$(bash "$ROOT/scripts/mokli_upgrade_section11_wait_quota_reset.sh" 2>&1 || true)
parsed=$(printf '%s\n' "$RESET_OUT" | sed -n 's/^seconds_until_reset=\([^ ]*\).*/\1/p' | tail -1)
[[ -n "$parsed" ]] && RESET_SEC="$parsed"

ENV_OK=0
ENV_COMBINED=""
if [[ "$SKIP_VPS" -eq 1 ]]; then
  echo "== VPS env skipped (--skip-vps) =="
  ENV_OK=1
  if [[ -d "$EVENTS" ]]; then
    echo "== cached LLM quota (local JSONL) =="
    bash "$ROOT/scripts/vps_section11_quota_status.sh" --local-dir "$EVENTS" || true
  fi
else
  echo "== VPS env (quota + OANDA required for full closure) =="
  set +e
  ENV_COMBINED=$(bash "$ROOT/scripts/vps_section11_env_check.sh" --require-quota --require-oanda 2>&1)
  ENV_EC=$?
  set -e
  printf '%s\n' "$ENV_COMBINED"
  if [[ "$ENV_EC" -eq 0 ]]; then
    ENV_OK=1
  fi
fi

echo ""
echo "== §11 artifacts (require-through $REQUIRE) =="
if [[ -d "$EVENTS" ]]; then
  section11_prune_row5_stale_no_nested "$EVENTS" "$ROOT"
fi
VAL_OK=0
set +e
VALID_COMBINED=$(
  bash "$ROOT/scripts/mokli_upgrade_section11_validate.sh" \
    --dir "$EVENTS" --results "$RESULTS" --require-through "$REQUIRE" 2>&1
)
VALID_EC=$?
set -e
printf '%s\n' "$VALID_COMBINED"
if [[ "$VALID_EC" -eq 0 ]]; then
  VAL_OK=1
else
  CLOSURE_ERRORS=$(printf '%s\n' "$VALID_COMBINED" | sed -n 's/^closure_errors=\([0-9]*\).*/\1/p' | tail -1)
  if [[ -z "${CLOSURE_ERRORS}" ]]; then
    CLOSURE_ERRORS=$(printf '%s\n' "$VALID_COMBINED" | grep -c '^ERROR' || true)
  fi
  if ! printf '%s\n' "$VALID_COMBINED" | grep -q '^closure_errors='; then
    echo "closure_errors=${CLOSURE_ERRORS}" >&2
  fi
fi

ALLOW_PARTIAL_CE=""
if [[ "$REQUIRE" -ge 13 && -d "$EVENTS" && -f "$RESULTS" ]]; then
  ALLOW_PARTIAL_CE=$(
    section11_allow_partial_closure_errors \
      "$PYTHON" "$ROOT/scripts/mokli_upgrade_section11_validate.py" \
      "$EVENTS" "$RESULTS" "$REQUIRE"
  )
fi

echo ""
if [[ "$ENV_OK" -eq 1 && "$VAL_OK" -eq 1 ]]; then
  echo "OK §11 blockers clear — run mokli_upgrade_section11_close.sh --apply --require-through $REQUIRE --results $RESULTS"
  echo "blockers_summary: env_ok=1 validate_ok=1 require=$REQUIRE closure_errors=0 allow_partial_closure_errors=0 live_rerun_rows=${RERUN_ROWS:-none} seconds_until_reset=$RESET_SEC"
  echo "BLOCKERS_EXIT=0"
  exit 0
fi

echo "BLOCKED §11 production closure (env_ok=$ENV_OK validate_ok=$VAL_OK)" >&2
echo "See: docs/mokli-agent-upgrade-operator-handoff.md (9-step checklist)" >&2
if [[ "$ENV_OK" -eq 0 && "$SKIP_VPS" -eq 0 ]]; then
  oanda_cfg=$(printf '%s\n' "$ENV_COMBINED" | sed -n 's/^oanda_configured=//p' | tail -1)
  oanda_ef=$(printf '%s\n' "$ENV_COMBINED" | sed -n 's/^oanda_env_file=//p' | tail -1)
  llm_q=$(printf '%s\n' "$ENV_COMBINED" | sed -n 's/^llm_quota=//p' | tail -1)
  if [[ "${llm_q:-}" == BLOCKED* ]]; then
    echo "NEXT quota: OpenRouter credits or export MOKLI_SECTION11_MODEL=… (docs/section11-vps-env.example)" >&2
  fi
  if [[ "${oanda_cfg:-}" == no ]]; then
    if [[ "${oanda_ef:-}" == present ]]; then
      echo "NEXT OANDA: OANDA_API_TOKEN=… OANDA_ACCOUNT_ID=… bash scripts/vps_section11_set_oanda_env.sh (.env on VPS exists; keys missing)" >&2
    else
      echo "NEXT OANDA: OANDA_API_TOKEN=… OANDA_ACCOUNT_ID=… bash scripts/vps_section11_set_oanda_env.sh" >&2
    fi
  fi
  if [[ -z "${oanda_cfg:-}" && -z "${llm_q:-}" ]]; then
    echo "NEXT env: export MOKLI_SECTION11_MODEL=… or OpenRouter credits; OANDA: bash scripts/vps_section11_set_oanda_env.sh" >&2
  fi
elif [[ "$ENV_OK" -eq 0 ]]; then
  echo "NEXT env: bash scripts/vps_section11_env_check.sh --require-quota --require-oanda" >&2
fi
if [[ "$VAL_OK" -eq 0 ]]; then
  after_p0="${EVENTS}/01-no-tools-after-p0.jsonl"
  if [[ ! -f "$after_p0" ]]; then
    echo "NEXT P0: bash scripts/vps_section11_row1_after_p0.sh (after quota OK)" >&2
  else
    ap_line=$("$PYTHON" "$ROOT/scripts/mokli_upgrade_diagnostic_extract.py" --file "$after_p0" 2>/dev/null || true)
    ap_in=$(section11_parse_probe_in "$ap_line")
    if [[ -z "${ap_in:-}" || "$ap_in" == "0" ]]; then
      echo "NEXT P0: 01-no-tools-after-p0.jsonl needs live in>0 — bash scripts/vps_section11_row1_after_p0.sh (after quota OK)" >&2
    fi
  fi
  echo "NEXT §11 live rows: ${RERUN_ROWS:-none} — bash scripts/mokli_upgrade_section11_rerun_partials.sh; then remaining_rows.sh (11–13)" >&2
  if [[ -f "$RESULTS" ]] && grep -q PARTIAL "$RESULTS" 2>/dev/null \
    && [[ "${CLOSURE_ERRORS:-}" =~ ^[0-9]+$ ]] && [[ "${CLOSURE_ERRORS}" -gt 2 ]]; then
    echo "HINT: strict closure_errors includes PARTIAL «النتيجة» + row 5/10 JSONL quality; markdown preview only: mokli_upgrade_section11_close.sh --allow-partial --require-through ${REQUIRE} (never with --apply)" >&2
  fi
fi
echo "Quick reruns when quota returns (live_rerun_rows=${RERUN_ROWS:-none}): bash scripts/mokli_upgrade_section11_rerun_partials.sh" >&2
echo "HINT: after reset — bash scripts/mokli_upgrade_section11_timer_wake.sh --wait-quota" >&2
printf '%s\n' "$RESET_OUT" \
  | grep -E 'seconds_until_reset=|OpenRouter free-tier' \
  | sed -e 's/^/HINT reset: /' -e 's/^HINT reset: HINT: /HINT reset: /' >&2 || true
echo "blockers_summary: env_ok=$ENV_OK validate_ok=$VAL_OK require=$REQUIRE closure_errors=${CLOSURE_ERRORS:-unknown} allow_partial_closure_errors=${ALLOW_PARTIAL_CE:-unknown} live_rerun_rows=${RERUN_ROWS:-none} seconds_until_reset=$RESET_SEC" >&2
echo "BLOCKERS_EXIT=1" >&2
exit 1
