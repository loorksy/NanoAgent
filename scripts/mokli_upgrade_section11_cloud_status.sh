#!/usr/bin/env bash
# Cloud Agent / workstation snapshot: VPS quota probe + local §11 blockers (no LLM, no pull).
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
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

echo "== VPS LLM quota (may exit 1 when blocked) =="
QUOTA_OK=0
if bash "$ROOT/scripts/vps_section11_quota_probe.sh"; then
  QUOTA_OK=1
fi

echo ""
echo "== Local §11 artifacts (--skip-vps) =="
BLOCK_OK=0
if bash "$ROOT/scripts/mokli_upgrade_section11_blockers.sh" \
  --skip-vps --require-through "$REQUIRE"; then
  BLOCK_OK=1
fi

echo ""
echo "cloud_status: quota_ok=$QUOTA_OK blockers_ok=$BLOCK_OK require_through=$REQUIRE"
if [[ "$QUOTA_OK" -eq 1 && "$BLOCK_OK" -eq 1 ]]; then
  echo "READY for section11_close.sh --apply --require-through $REQUIRE"
  exit 0
fi
exit 1
