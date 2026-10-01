#!/usr/bin/env bash
# §11 row 12 helper: verify Mokli UI + Agent API on VPS; reminds operator to chat via UI pipe.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/vps_ssh.sh
source "$ROOT/scripts/vps_ssh.sh"

HOST="${MOKLI_SSH_HOST:-hostinger-vps}"
INSTALL_DIR="${MOKLI_INSTALL_DIR:-/opt/nanoagent}"

if ! vps_ssh_ready; then
  bash "$ROOT/scripts/cloud_agent_vps_secrets_check.sh" >&2 || true
  exit 1
fi

vps_ssh bash -s -- "$INSTALL_DIR" <<'EOS'
set -euo pipefail
INSTALL="$1"
UI=http://127.0.0.1:8080
API=http://127.0.0.1:8766/api/v2
curl -sf -o /dev/null -w "ui_http=%{http_code}\n" "$UI/"
curl -sf "$API/health" | python3 -c "import sys,json; d=json.load(sys.stdin); print('agent_api_ok', d.get('ok'))"
test -f "$INSTALL/deploy/mokliui/functions/mokli_pipe.py" && grep -q SHOW_DIAGNOSTICS "$INSTALL/deploy/mokliui/functions/mokli_pipe.py" && echo "pipe_show_diagnostics=present"
EOS

cat <<'NOTE'

§11 row 12 (desktop) — operator steps (after quota probe passes):
  1. Open WebUI → Admin → Functions → Mokli pipe → enable SHOW_DIAGNOSTICS (and SHOW_TIMELINE if desired).
  2. Chat in Mokli UI (Arabic gold question or «حلل الذهب») through the pipe, not raw Agent API.
  3. Save pipe/gateway JSONL (diagnostic + tool + structured/decision events) as section11-events/12-desktop-ui.jsonl.
  4. Screenshot: activity line wrap + Arabic decision card.
  5. Pull artifacts: bash scripts/vps_section11_pull_events.sh

NOTE
