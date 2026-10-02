#!/usr/bin/env bash
# Pull §11 JSONL from VPS, print P0 table/interim delta, validate rows 1..N (no LLM).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/section11_quota_hints.sh
source "$ROOT/scripts/section11_quota_hints.sh"
PULL_VPS=0
POSITIONAL=()

usage() {
  echo "Usage: $0 [--pull-vps] [EVENTS_DIR] [RESULTS_JSON] [REQUIRE_THROUGH]" >&2
  echo "  --pull-vps  fast-forward VPS checkout (§11 branch) before scp" >&2
  echo "  REQUIRE_THROUGH is numeric (13), not @13; default events dir is section11-events/" >&2
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --pull-vps) PULL_VPS=1; shift ;;
    -h | --help) usage ;;
    --) shift; POSITIONAL+=("$@"); break ;;
    -*) echo "Unknown option: $1" >&2; usage ;;
    *) POSITIONAL+=("$1"); shift ;;
  esac
done

EVENTS="${POSITIONAL[0]:-$ROOT/section11-events}"
RESULTS="${POSITIONAL[1]:-$ROOT/section11-results-partial.json}"
REQUIRE="${POSITIONAL[2]:-13}"

if [[ "$PULL_VPS" -eq 1 ]]; then
  branch="${MOKLI_SECTION11_VPS_BRANCH:-cursor/section11-vps-rows-d9e1}"
  echo "== fast-forward VPS ($branch) =="
  bash "$ROOT/scripts/vps_pull_main.sh" "$branch"
fi

echo "== pull from VPS =="
bash "$ROOT/scripts/vps_section11_pull_events.sh" "$EVENTS"

# Legacy status.sh wrote quota-status-*.jsonl into events; drop on sync (not §11 rows).
rm -f "$EVENTS"/quota-status-*.jsonl 2>/dev/null || true

echo ""
bash "$ROOT/scripts/mokli_upgrade_section11_after_pull.sh" "$EVENTS" "$RESULTS" "$REQUIRE"

echo ""
echo "== cached quota probe (local JSONL, no LLM) =="
bash "$ROOT/scripts/vps_section11_quota_status.sh" --local-dir "$EVENTS" || true

echo ""
if [[ -f "$EVENTS/01-no-tools-after-p0.jsonl" ]]; then
  echo "HINT: after full §11 JSONL — section11_close.sh --apply --require-through 13 --results section11-results-partial.json"
else
  echo "HINT: after quota — vps_section11_row1_after_p0.sh then close --apply @13 for §2.1 live delta_in"
fi

VALIDATE_OK=0
CLOSURE_ERRORS=""
set +e
VALID_OUT=$(
  bash "$ROOT/scripts/mokli_upgrade_section11_validate.sh" \
    --dir "$EVENTS" --results "$RESULTS" --require-through "$REQUIRE" 2>&1
)
VALID_EC=$?
set -e
CLOSURE_ERRORS=$(printf '%s\n' "$VALID_OUT" | sed -n 's/^closure_errors=\([0-9]*\).*/\1/p' | tail -1)
if [[ "$VALID_EC" -eq 0 ]]; then
  VALIDATE_OK=1
  CLOSURE_ERRORS=${CLOSURE_ERRORS:-0}
  echo "OK sync from VPS (artifacts through row $REQUIRE validated locally)"
else
  echo "INCOMPLETE sync from VPS (P0 table/delta refreshed; rows 1–$REQUIRE not closable yet)" >&2
  printf '%s\n' "$VALID_OUT" | grep -E '^ERROR |^HINT row |^closure_errors=' | head -20 >&2 || true
fi
echo "sync_summary: validate_ok=$VALIDATE_OK require=$REQUIRE closure_errors=${CLOSURE_ERRORS:-unknown}"
