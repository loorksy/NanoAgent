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
  echo "HINT secrets are registered but not exported to this shell." >&2
  echo "  1. In Cloud Agent environment settings, save secrets as VPS and VPSPASS" >&2
  echo "     (or vps and password — mapped by scripts/vps_env.sh)." >&2
  echo "  2. Start a new agent run so values are injected into the process environment." >&2
  echo "  3. Or export manually in the shell before deploy (not committed to git)." >&2
fi

exit 1
