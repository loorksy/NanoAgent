#!/usr/bin/env bash
# Verify Cloud Agent / shell has VPS deploy credentials without printing values.
# Exit 0 when VPS and VPSPASS are non-empty after scripts/vps_env.sh mapping.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/vps_env.sh
source "$ROOT/scripts/vps_env.sh"

vps_ok=0
pass_ok=0
[[ -n "${VPS:-}" ]] && vps_ok=1
[[ -n "${VPSPASS:-}" ]] && pass_ok=1

if [[ -n "${MOKLI_SSH_HOST:-}" ]]; then
  if ssh -o BatchMode=yes -o ConnectTimeout=15 "$MOKLI_SSH_HOST" true 2>/dev/null; then
    echo "OK  VPS SSH key auth (MOKLI_SSH_HOST=$MOKLI_SSH_HOST)"
    exit 0
  fi
  echo "FAIL MOKLI_SSH_HOST=$MOKLI_SSH_HOST — key auth failed (BatchMode)" >&2
  exit 1
fi

if [[ "$vps_ok" -eq 1 && "$pass_ok" -eq 1 ]]; then
  echo "OK  VPS deploy credentials present (VPS + VPSPASS)"
  exit 0
fi

echo "FAIL VPS deploy credentials missing" >&2
[[ "$vps_ok" -eq 0 ]] && echo "  - VPS unset (map from secret vps via scripts/vps_env.sh)" >&2
[[ "$pass_ok" -eq 0 ]] && echo "  - VPSPASS unset (map from secret password)" >&2

if [[ -n "${CLOUD_AGENT_ALL_SECRET_NAMES:-}" ]]; then
  echo "INFO registered secret names: ${CLOUD_AGENT_ALL_SECRET_NAMES}" >&2
fi
if [[ -n "${CLOUD_AGENT_INJECTED_SECRET_NAMES:-}" ]]; then
  echo "INFO injected secret names: ${CLOUD_AGENT_INJECTED_SECRET_NAMES}" >&2
fi

if [[ -n "${CLOUD_AGENT_INJECTED_SECRET_NAMES:-}" && "$vps_ok" -eq 0 && "$pass_ok" -eq 0 ]]; then
  echo "HINT secret names are injected into this run but VPS/VPSPASS values are empty." >&2
  echo "  Re-enter values in Cloud Agent environment secrets (not just names), then start a new agent run." >&2
  echo "  Preferred names: VPS + VPSPASS; legacy vps + password map via scripts/vps_env.sh." >&2
  echo "  Or export VPS/VPSPASS manually in the shell before deploy (never commit them)." >&2
fi

exit 1
