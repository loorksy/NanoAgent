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
REQUIRE="${POSITIONAL[2]:-10}"

if [[ "$PULL_VPS" -eq 1 ]]; then
  branch="${MOKLI_SECTION11_VPS_BRANCH:-cursor/section11-vps-rows-d9e1}"
  echo "== fast-forward VPS ($branch) =="
  bash "$ROOT/scripts/vps_pull_main.sh" "$branch"
fi

echo "== pull from VPS =="
bash "$ROOT/scripts/vps_section11_pull_events.sh" "$EVENTS"

# Legacy status.sh wrote quota-status-*.jsonl into events; drop on sync (not §11 rows).
rm -f "$EVENTS"/quota-status-*.jsonl 2>/dev/null || true
section11_prune_row5_stale_no_nested "$EVENTS" "$ROOT"

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
echo "OK sync from VPS (artifacts through row $REQUIRE validated locally)"
