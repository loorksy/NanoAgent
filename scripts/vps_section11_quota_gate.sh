#!/usr/bin/env bash
# Live quota probe, or recent cached quota-probe.jsonl when upstream 429 flips between §11 rows.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-quota-probe.jsonl}"

if bash "$ROOT/scripts/vps_section11_quota_probe.sh" "$OUT"; then
  exit 0
fi

if [[ "$OUT" != "quota-probe.jsonl" ]]; then
  if MOKLI_QUOTA_STATUS_MAX_AGE_MIN="${MOKLI_QUOTA_GATE_MAX_AGE_MIN:-45}" \
    bash "$ROOT/scripts/vps_section11_quota_status.sh" \
      --local-dir "$ROOT/section11-events" --require-fresh; then
    echo "WARN: ${OUT} probe blocked; continuing on fresh cached quota-probe.jsonl" >&2
    exit 0
  fi
fi

exit 1
