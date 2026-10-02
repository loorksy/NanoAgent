#!/usr/bin/env bash
# VPS §11 readiness snapshot: git rev, API health, OANDA .env, LLM quota (no secret values).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/vps_ssh.sh
source "$ROOT/scripts/vps_ssh.sh"
# shellcheck source=scripts/section11_quota_hints.sh
source "$ROOT/scripts/section11_quota_hints.sh"
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

_read_gateway_model_preset() {
  local user="${1:-${MOKLI_SERVICE_USER:-nanoagent}}"
  if [[ "$(id -un)" == "$user" ]]; then
    python3 - <<'PY' 2>/dev/null || echo unknown
import json
from pathlib import Path

p = Path.home() / ".mokli" / "config.json"
if not p.is_file():
    print("missing")
else:
    data = json.loads(p.read_text(encoding="utf-8"))
    agents = data.get("agents") or {}
    defaults = agents.get("defaults") or {}
    print(defaults.get("modelPreset") or "null")
PY
  elif id "$user" &>/dev/null; then
    sudo -u "$user" python3 - <<'PY' 2>/dev/null || echo unknown
import json
from pathlib import Path

p = Path.home() / ".mokli" / "config.json"
if not p.is_file():
    print("missing")
else:
    data = json.loads(p.read_text(encoding="utf-8"))
    agents = data.get("agents") or {}
    defaults = agents.get("defaults") or {}
    print(defaults.get("modelPreset") or "null")
PY
  else
    echo unknown
  fi
}

_snapshot_body() {
  local install="$1"
  local rev health oanda ui_http pipe_diag
  rev=$(git -C "$install" rev-parse --short HEAD 2>/dev/null || echo unknown)
  branch=$(git -C "$install" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)
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
  model_preset=$(_read_gateway_model_preset "$SERVICE_USER")
  echo "REV=$rev"
  echo "BRANCH=$branch"
  echo "API_HEALTH=$health"
  echo "OANDA=$oanda"
  echo "UI_HTTP=$ui_http"
  echo "PIPE_DIAG=$pipe_diag"
  echo "MODEL_PRESET=$model_preset"
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
branch=$(git -C "$install" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)
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
model_preset=unknown
model_preset=$(python3 - <<'PY' 2>/dev/null || echo unknown
import json
from pathlib import Path

p = Path.home() / ".mokli" / "config.json"
if not p.is_file():
    print("missing")
else:
    data = json.loads(p.read_text(encoding="utf-8"))
    agents = data.get("agents") or {}
    defaults = agents.get("defaults") or {}
    print(defaults.get("modelPreset") or "null")
PY
)
echo "REV=$rev"
echo "BRANCH=$branch"
echo "API_HEALTH=$health"
echo "OANDA=$oanda"
echo "UI_HTTP=$ui_http"
echo "PIPE_DIAG=$pipe_diag"
echo "MODEL_PRESET=$model_preset"
INNER
EOS
)
else
  bash "$ROOT/scripts/cloud_agent_vps_secrets_check.sh" >&2 || true
  exit 1
fi

rev=$(echo "$lines" | sed -n 's/^REV=//p')
branch=$(echo "$lines" | sed -n 's/^BRANCH=//p')
health=$(echo "$lines" | sed -n 's/^API_HEALTH=//p')
oanda=$(echo "$lines" | sed -n 's/^OANDA=//p')
ui_http=$(echo "$lines" | sed -n 's/^UI_HTTP=//p')
pipe_diag=$(echo "$lines" | sed -n 's/^PIPE_DIAG=//p')
model_preset=$(echo "$lines" | sed -n 's/^MODEL_PRESET=//p')

echo "git_rev=${rev:-?}"
echo "git_branch=${branch:-?}"
echo "agent_api_health=${health:-?}"
echo "oanda_configured=${oanda:-?}"
echo "mokli_ui_http=${ui_http:-?}"
echo "mokli_pipe_show_diagnostics=${pipe_diag:-?}"
echo "gateway_model_preset=${model_preset:-?}"
if [[ -n "${MOKLI_SECTION11_MODEL:-}" ]]; then
  echo "section11_model_override=set"
else
  echo "section11_model_override=unset"
fi

expected_branch="${MOKLI_SECTION11_VPS_BRANCH:-cursor/section11-vps-rows-d9e1}"
if [[ -n "${branch:-}" && "$branch" != "$expected_branch" ]]; then
  echo "HINT: VPS on branch=${branch} — §11 tooling expects ${expected_branch} until PR merge" >&2
  echo "HINT: bash scripts/vps_pull_main.sh ${expected_branch}" >&2
fi
local_rev=$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo unknown)
if [[ -n "${rev:-}" && "$rev" != unknown && "$local_rev" != unknown && "$rev" != "$local_rev" ]]; then
  echo "HINT: VPS git_rev=${rev} != local ${local_rev} — bash scripts/vps_pull_main.sh ${expected_branch}" >&2
fi

quota_ok=0
quota_line=""
if [[ "$REQUIRE_QUOTA" -eq 1 ]]; then
  if quota_line=$(bash "$ROOT/scripts/vps_section11_quota_probe.sh" 2>&1); then
    quota_ok=1
    echo "llm_quota=OK (live probe)"
  else
    echo "llm_quota=BLOCKED (live probe)"
    if quota_line=$(bash "$ROOT/scripts/vps_section11_quota_status.sh" --local-dir "$ROOT/section11-events" 2>&1); then
      quota_ok=1
      echo "llm_quota=OK (cached probe; upstream 429 between turns)"
    fi
  fi
else
  if quota_line=$(bash "$ROOT/scripts/vps_section11_quota_status.sh" 2>&1); then
    quota_ok=1
    echo "llm_quota=OK (cached)"
  else
    echo "llm_quota=BLOCKED (cached)"
  fi
fi
if [[ -n "${quota_line:-}" ]]; then
  printf '%s\n' "$quota_line" | grep -E '^(probe=|QUOTA_|MISSING|STALE|INVALID)' || true
fi

fail=0
if [[ "$REQUIRE_OANDA" -eq 1 && "${oanda:-}" != yes ]]; then
  echo "BLOCKED: set OANDA_* in ${INSTALL_DIR}/.env (see docs/section11-vps-env.example)" >&2
  fail=1
fi
if [[ "$REQUIRE_QUOTA" -eq 1 && "$quota_ok" -eq 0 ]]; then
  echo "BLOCKED: LLM quota (gateway preset=${model_preset:-?}; credits or MOKLI_SECTION11_MODEL on this shell)" >&2
  section11_print_quota_unblock_hints
  fail=1
elif [[ "$quota_ok" -eq 0 ]]; then
  echo "HINT: llm_quota blocked — use --require-quota before live §11 turns (exit 1)" >&2
  section11_print_quota_unblock_hints
fi
exit "$fail"
