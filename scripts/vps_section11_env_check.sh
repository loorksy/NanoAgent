#!/usr/bin/env bash
# VPS §11 readiness snapshot: git rev, API health, OANDA .env, LLM quota (no secret values).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/vps_ssh.sh
source "$ROOT/scripts/vps_ssh.sh"
# shellcheck source=scripts/section11_agent_api_turn_core.sh
source "$ROOT/scripts/section11_agent_api_turn_core.sh"

INSTALL_DIR="${MOKLI_INSTALL_DIR:-/opt/nanoagent}"
SERVICE_USER="${MOKLI_SERVICE_USER:-nanoagent}"
HOST="${MOKLI_SSH_HOST:-hostinger-vps}"
export MOKLI_SSH_HOST="$HOST"
REQUIRE_OANDA=0
REQUIRE_QUOTA=0

usage() {
  echo "Usage: $0 [--require-oanda] [--require-quota]" >&2
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --require-oanda) REQUIRE_OANDA=1; shift ;;
    --require-quota) REQUIRE_QUOTA=1; shift ;;
    -h | --help) usage ;;
    *) echo "Unknown arg: $1" >&2; usage ;;
  esac
done

_snapshot_body() {
  local install="$1"
  local rev health oanda ui_http pipe_diag
  rev=$(git -C "$install" rev-parse --short HEAD 2>/dev/null || echo unknown)
  health=fail
  curl -sf http://127.0.0.1:8766/api/v2/health >/dev/null 2>&1 && health=ok
  ui_http=000
  ui_http=$(curl -sf -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/ 2>/dev/null || echo 000)
  pipe_diag=missing
  if [[ -f "$install/deploy/mokliui/functions/mokli_pipe.py" ]] \
    && grep -q SHOW_DIAGNOSTICS "$install/deploy/mokliui/functions/mokli_pipe.py" 2>/dev/null; then
    pipe_diag=present
  fi
  oanda=no
  if [[ -f "$install/.env" ]] \
    && grep -qE '^OANDA_API_TOKEN=.+' "$install/.env" 2>/dev/null \
    && grep -qE '^OANDA_ACCOUNT_ID=.+' "$install/.env" 2>/dev/null; then
    oanda=yes
  fi
  echo "REV=$rev"
  echo "API_HEALTH=$health"
  echo "OANDA=$oanda"
  echo "UI_HTTP=$ui_http"
  echo "PIPE_DIAG=$pipe_diag"
}

if section11_local_ready "$INSTALL_DIR"; then
  lines=$(_snapshot_body "$INSTALL_DIR")
elif vps_ssh_ready; then
  lines=$(vps_ssh bash -s -- "$INSTALL_DIR" "$SERVICE_USER" <<'EOS'
set -euo pipefail
install="$1"
user="$2"
sudo -u "$user" bash -s -- "$install" <<'INNER'
install="$1"
rev=$(git -C "$install" rev-parse --short HEAD 2>/dev/null || echo unknown)
health=fail
curl -sf http://127.0.0.1:8766/api/v2/health >/dev/null 2>&1 && health=ok
ui_http=000
ui_http=$(curl -sf -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/ 2>/dev/null || echo 000)
pipe_diag=missing
if [[ -f "$install/deploy/mokliui/functions/mokli_pipe.py" ]] \
  && grep -q SHOW_DIAGNOSTICS "$install/deploy/mokliui/functions/mokli_pipe.py" 2>/dev/null; then
  pipe_diag=present
fi
oanda=no
if [[ -f "$install/.env" ]] \
  && grep -qE '^OANDA_API_TOKEN=.+' "$install/.env" 2>/dev/null \
  && grep -qE '^OANDA_ACCOUNT_ID=.+' "$install/.env" 2>/dev/null; then
  oanda=yes
fi
echo "REV=$rev"
echo "API_HEALTH=$health"
echo "OANDA=$oanda"
echo "UI_HTTP=$ui_http"
echo "PIPE_DIAG=$pipe_diag"
INNER
EOS
)
else
  bash "$ROOT/scripts/cloud_agent_vps_secrets_check.sh" >&2 || true
  exit 1
fi

rev=$(echo "$lines" | sed -n 's/^REV=//p')
health=$(echo "$lines" | sed -n 's/^API_HEALTH=//p')
oanda=$(echo "$lines" | sed -n 's/^OANDA=//p')
ui_http=$(echo "$lines" | sed -n 's/^UI_HTTP=//p')
pipe_diag=$(echo "$lines" | sed -n 's/^PIPE_DIAG=//p')

echo "git_rev=${rev:-?}"
echo "agent_api_health=${health:-?}"
echo "oanda_configured=${oanda:-?}"
echo "mokli_ui_http=${ui_http:-?}"
echo "mokli_pipe_show_diagnostics=${pipe_diag:-?}"

quota_ok=0
quota_line=""
if quota_line=$(bash "$ROOT/scripts/vps_section11_quota_probe.sh" 2>&1); then
  quota_ok=1
  echo "llm_quota=OK"
else
  echo "llm_quota=BLOCKED"
fi
printf '%s\n' "$quota_line" | tail -1

fail=0
if [[ "$REQUIRE_OANDA" -eq 1 && "${oanda:-}" != yes ]]; then
  echo "BLOCKED: set OANDA_* in ${INSTALL_DIR}/.env (see docs/section11-vps-env.example)" >&2
  fail=1
fi
if [[ "$REQUIRE_QUOTA" -eq 1 && "$quota_ok" -eq 0 ]]; then
  echo "BLOCKED: LLM quota (OpenRouter credits or paid preset)" >&2
  fail=1
elif [[ "$quota_ok" -eq 0 ]]; then
  echo "HINT: llm_quota blocked — use --require-quota before live §11 turns (exit 1)" >&2
  echo "HINT: or set paid preset: export MOKLI_SECTION11_MODEL=… (docs/section11-vps-env.example)" >&2
fi
exit "$fail"
