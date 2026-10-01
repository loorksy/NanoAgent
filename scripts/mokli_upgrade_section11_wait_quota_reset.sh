#!/usr/bin/env bash
# Wait until OpenRouter X-RateLimit-Reset (from quota-probe JSONL), then live quota probe.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${ROOT}/.venv/bin/python"
[[ -x "$PYTHON" ]] || PYTHON=python3
PROBE="${ROOT}/section11-events/quota-probe.jsonl"
DO_WAIT=0
MAX_WAIT_SEC=86400
BUFFER_SEC=120

usage() {
  echo "Usage: $0 [--wait] [--probe PATH] [--max-wait SEC] [--buffer SEC]" >&2
  echo "  Without --wait: print seconds until reset and exit 0 (0 = reset passed or unknown)." >&2
  echo "  With --wait: sleep until reset+buffer, then bash scripts/vps_section11_quota_probe.sh" >&2
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --wait) DO_WAIT=1; shift ;;
    --probe) PROBE="$2"; shift 2 ;;
    --max-wait) MAX_WAIT_SEC="$2"; shift 2 ;;
    --buffer) BUFFER_SEC="$2"; shift 2 ;;
    -h | --help) usage ;;
    *) echo "Unknown arg: $1" >&2; usage ;;
  esac
done

raw_secs=$("$PYTHON" "$ROOT/scripts/section11_quota_reset_hint.py" --seconds "$PROBE")
if [[ "$raw_secs" == "-1" ]]; then
  echo "WARN: no X-RateLimit-Reset in $PROBE — run vps_section11_quota_probe.sh first" >&2
  secs=0
else
  secs="$raw_secs"
fi

echo "seconds_until_reset=$secs buffer_sec=$BUFFER_SEC"

if [[ "$DO_WAIT" -eq 0 ]]; then
  exit 0
fi

if [[ "$secs" -gt 0 ]]; then
  sleep_for=$(( secs + BUFFER_SEC ))
  if [[ "$sleep_for" -gt "$MAX_WAIT_SEC" ]]; then
    echo "ERROR: wait $sleep_for sec exceeds --max-wait $MAX_WAIT_SEC" >&2
    exit 1
  fi
  echo "Sleeping ${sleep_for}s until reset+buffer…" >&2
  sleep "$sleep_for"
fi

exec bash "$ROOT/scripts/vps_section11_quota_probe.sh"
