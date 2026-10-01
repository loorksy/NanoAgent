#!/usr/bin/env bash
# One-page §11 production blockers: VPS env + validate through 13 (exit 1 if not closable).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
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

ENV_OK=0
if [[ "$SKIP_VPS" -eq 1 ]]; then
  echo "== VPS env skipped (--skip-vps) =="
  ENV_OK=1
  if [[ -d "$EVENTS" ]]; then
    echo "== cached LLM quota (local JSONL) =="
    bash "$ROOT/scripts/vps_section11_quota_status.sh" --local-dir "$EVENTS" || true
  fi
else
  echo "== VPS env (quota + OANDA required for full closure) =="
  if bash "$ROOT/scripts/vps_section11_env_check.sh" --require-quota --require-oanda; then
    ENV_OK=1
  fi
fi

echo ""
echo "== §11 artifacts (require-through $REQUIRE) =="
VAL_OK=0
if bash "$ROOT/scripts/mokli_upgrade_section11_validate.sh" \
  --dir "$EVENTS" --results "$RESULTS" --require-through "$REQUIRE"; then
  VAL_OK=1
fi

echo ""
if [[ "$ENV_OK" -eq 1 && "$VAL_OK" -eq 1 ]]; then
  echo "OK §11 blockers clear — run mokli_upgrade_section11_close.sh --apply --require-through $REQUIRE"
  echo "BLOCKERS_EXIT=0"
  exit 0
fi

echo "BLOCKED §11 production closure (env_ok=$ENV_OK validate_ok=$VAL_OK)" >&2
echo "See: docs/mokli-agent-upgrade-operator-handoff.md (9-step checklist)" >&2
if [[ "$ENV_OK" -eq 0 && "$SKIP_VPS" -eq 0 ]]; then
  echo "NEXT env: export MOKLI_SECTION11_MODEL=… or OpenRouter credits; OANDA: bash scripts/vps_section11_set_oanda_env.sh" >&2
elif [[ "$ENV_OK" -eq 0 ]]; then
  echo "NEXT env: bash scripts/vps_section11_env_check.sh --require-quota --require-oanda" >&2
fi
if [[ "$VAL_OK" -eq 0 ]]; then
  if [[ ! -f "$EVENTS/01-no-tools-after-p0.jsonl" ]]; then
    echo "NEXT P0: bash scripts/vps_section11_row1_after_p0.sh (after quota OK)" >&2
  fi
  echo "NEXT §11: bash scripts/mokli_upgrade_section11_rerun_partials.sh; then remaining_rows.sh (11–13)" >&2
fi
echo "Quick reruns when quota returns: bash scripts/mokli_upgrade_section11_rerun_partials.sh" >&2
echo "HINT: after reset — bash scripts/mokli_upgrade_section11_timer_wake.sh --wait-quota" >&2
bash "$ROOT/scripts/mokli_upgrade_section11_wait_quota_reset.sh" 2>&1 \
  | grep -E 'seconds_until_reset=|OpenRouter free-tier' \
  | sed -e 's/^/HINT reset: /' -e 's/^HINT reset: HINT: /HINT reset: /' >&2 || true
echo "BLOCKERS_EXIT=1" >&2
exit 1
