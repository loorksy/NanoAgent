#!/usr/bin/env bash
# §11 row 1 re-run for live P0 after: quota OK → greeting turn → delta vs baseline JSONL.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/vps_ssh.sh
source "$ROOT/scripts/vps_ssh.sh"
# shellcheck source=scripts/section11_agent_api_turn_core.sh
source "$ROOT/scripts/section11_agent_api_turn_core.sh"

export MOKLI_SSH_HOST="${MOKLI_SSH_HOST:-hostinger-vps}"
INSTALL_DIR="${MOKLI_INSTALL_DIR:-/opt/nanoagent}"
SERVICE_USER="${MOKLI_SERVICE_USER:-nanoagent}"
OUT="${1:-01-no-tools-after-p0.jsonl}"
BASELINE="${2:-01-no-tools.jsonl}"
PROMPT="${3:-مرحبا، ما اسمك؟}"

echo "== quota probe (must pass) =="
bash "$ROOT/scripts/vps_section11_quota_probe.sh" || {
  echo "Abort row 1 after P0: fix LLM quota first" >&2
  exit 1
}

_run_delta_on_install() {
  local install="$1"
  sudo -u "${SERVICE_USER}" bash -lc "
set -euo pipefail
cd '$install'
source .venv/bin/activate
BASE='$BASELINE'
if [[ ! -f section11-events/\$BASE ]]; then
  RES=\$(python scripts/mokli_upgrade_diagnostic_extract.py --resolve-row 1 --dir section11-events --exclude-stem after-p0 2>/dev/null || true)
  if [[ -n \"\$RES\" && -f \"\$RES\" ]]; then
    BASE=\$(basename \"\$RES\")
  fi
fi
if [[ ! -f section11-events/\$BASE ]]; then
  echo \"Missing baseline row 1 JSONL on VPS (need 01-*.jsonl with diagnostic)\" >&2
  exit 1
fi
bash scripts/mokli_upgrade_p0_live_delta.sh section11-events/\$BASE section11-events/$OUT
"
}

echo "== §11 row 1 after P0 ($OUT) =="
bash "$ROOT/scripts/vps_section11_agent_api_turn.sh" "$OUT" "$PROMPT"

echo "== P0 live delta =="
if section11_local_ready "$INSTALL_DIR"; then
  _run_delta_on_install "$INSTALL_DIR"
elif vps_ssh_ready; then
  vps_ssh bash -s -- "$INSTALL_DIR" "$SERVICE_USER" "$BASELINE" "$OUT" <<'EOS'
set -euo pipefail
INSTALL="$1"
USER="$2"
BASE="$3"
NEW="$4"
sudo -u "$USER" bash -lc "
set -euo pipefail
cd '$INSTALL'
source .venv/bin/activate
BASE='$BASE'
if [[ ! -f section11-events/\$BASE ]]; then
  RES=\$(python scripts/mokli_upgrade_diagnostic_extract.py --resolve-row 1 --dir section11-events --exclude-stem after-p0 2>/dev/null || true)
  if [[ -n \"\$RES\" && -f \"\$RES\" ]]; then
    BASE=\$(basename \"\$RES\")
  fi
fi
if [[ ! -f section11-events/\$BASE ]]; then
  echo \"Missing baseline row 1 JSONL on VPS\" >&2
  exit 1
fi
bash scripts/mokli_upgrade_p0_live_delta.sh section11-events/\$BASE section11-events/$NEW
"
EOS
else
  bash "$ROOT/scripts/cloud_agent_vps_secrets_check.sh" >&2 || true
  exit 1
fi

echo "OK row 1 after P0 — sync results; section11_close --apply refreshes report §11 + §2.1 table"
