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

echo "== VPS LLM quota (cached probe; no new LLM call) =="
QUOTA_OK=0
if bash "$ROOT/scripts/vps_section11_quota_status.sh"; then
  QUOTA_OK=1
else
  echo "HINT: live probe: bash scripts/vps_section11_quota_probe.sh" >&2
fi

echo ""
echo "== VPS env snapshot (SSH; no live LLM turn) =="
# shellcheck source=scripts/vps_ssh.sh
source "$ROOT/scripts/vps_ssh.sh"
if vps_ssh_ready; then
  install="${MOKLI_INSTALL_DIR:-/opt/nanoagent}"
  vps_ssh "cd $(printf '%q' "$install") && bash scripts/vps_section11_env_check.sh" 2>&1 \
    | grep -E '^(git_rev|agent_api_health|oanda_configured|mokli_ui_http|mokli_pipe_show_diagnostics)=' \
    || echo "WARN: vps_section11_env_check failed" >&2
else
  echo "SKIP: set MOKLI_SSH_HOST or VPS+VPSPASS for VPS snapshot" >&2
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
if [[ "$BLOCK_OK" -eq 0 && "$REQUIRE" -gt 10 ]]; then
  if bash "$ROOT/scripts/mokli_upgrade_section11_blockers.sh" \
    --skip-vps --require-through 10 >/dev/null 2>&1; then
    echo "HINT: local artifacts rows 1–10 OK — bash $0 --require-through 10" >&2
  fi
fi
if [[ "$QUOTA_OK" -eq 1 && "$BLOCK_OK" -eq 1 ]]; then
  echo "READY for section11_close.sh --apply --require-through $REQUIRE"
  exit 0
fi
exit 1
