#!/usr/bin/env bash
# Pull §11 JSONL from VPS, print P0 table/interim delta, validate rows 1..N (no LLM).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVENTS="${1:-$ROOT/section11-events}"
RESULTS="${2:-$ROOT/section11-results-partial.json}"
REQUIRE="${3:-10}"

echo "== pull from VPS =="
bash "$ROOT/scripts/vps_section11_pull_events.sh" "$EVENTS"

echo ""
bash "$ROOT/scripts/mokli_upgrade_section11_after_pull.sh" "$EVENTS" "$RESULTS" "$REQUIRE"

echo ""
echo "OK sync from VPS (artifacts through row $REQUIRE validated locally)"
