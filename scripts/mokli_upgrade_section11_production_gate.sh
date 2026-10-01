#!/usr/bin/env bash
# Operator gate before §11 close --apply: VPS readiness + local artifacts through row N.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVENTS="${ROOT}/section11-events"
RESULTS="${ROOT}/section11-results-partial.json"
REQUIRE=13
SKIP_OANDA=0
SKIP_PULL=0

usage() {
  echo "Usage: $0 [--require-through N] [--results PATH] [--skip-oanda] [--skip-pull]" >&2
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --require-through) REQUIRE="$2"; shift 2 ;;
    --results) RESULTS="$2"; shift 2 ;;
    --skip-oanda) SKIP_OANDA=1; shift ;;
    --skip-pull) SKIP_PULL=1; shift ;;
    -h | --help) usage ;;
    *) echo "Unknown arg: $1" >&2; usage ;;
  esac
done

ENV_ARGS=(--require-quota)
if [[ "$SKIP_OANDA" -eq 0 ]]; then
  ENV_ARGS+=(--require-oanda)
fi

echo "== VPS env (quota + OANDA) =="
bash "${ROOT}/scripts/vps_section11_env_check.sh" "${ENV_ARGS[@]}"

if [[ "$SKIP_PULL" -eq 0 ]]; then
  bash "${ROOT}/scripts/mokli_upgrade_section11_sync_from_vps.sh" "$EVENTS" "$RESULTS" 10
fi

echo "== §11 blockers (artifacts only; env checked above) =="
bash "${ROOT}/scripts/mokli_upgrade_section11_blockers.sh" \
  --skip-vps --require-through "$REQUIRE" "$EVENTS" "$RESULTS"

echo "OK production gate passed — run section11_close.sh --apply --require-through $REQUIRE when results JSON is final"
