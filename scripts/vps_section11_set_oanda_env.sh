#!/usr/bin/env bash
# Merge OANDA_* from the caller environment into VPS /opt/nanoagent/.env (values never printed).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/vps_ssh.sh
source "$ROOT/scripts/vps_ssh.sh"

export MOKLI_SSH_HOST="${MOKLI_SSH_HOST:-hostinger-vps}"
INSTALL_DIR="${MOKLI_INSTALL_DIR:-/opt/nanoagent}"
SERVICE_USER="${MOKLI_SERVICE_USER:-nanoagent}"
SERVICE_UNIT="${MOKLI_GATEWAY_SERVICE:-nanoagent-gateway}"
MARKER="# --- OANDA (mokli §11) ---"

if [[ -z "${OANDA_API_TOKEN:-}" || -z "${OANDA_ACCOUNT_ID:-}" ]]; then
  echo "Usage: OANDA_API_TOKEN=… OANDA_ACCOUNT_ID=… [OANDA_ENV=practice] $0" >&2
  echo "See docs/section11-vps-env.example" >&2
  exit 1
fi

OANDA_ENV="${OANDA_ENV:-practice}"
TOKEN_B64=$(printf '%s' "$OANDA_API_TOKEN" | base64 -w0)
ACCOUNT_B64=$(printf '%s' "$OANDA_ACCOUNT_ID" | base64 -w0)

if ! vps_ssh_ready; then
  bash "$ROOT/scripts/cloud_agent_vps_secrets_check.sh" >&2 || true
  exit 1
fi

vps_ssh bash -s -- "$INSTALL_DIR" "$SERVICE_USER" "$SERVICE_UNIT" "$MARKER" "$OANDA_ENV" \
  "$TOKEN_B64" "$ACCOUNT_B64" <<'EOS'
set -euo pipefail
INSTALL="$1"
USER="$2"
UNIT="$3"
MARKER="$4"
OANDA_ENV="$5"
TOKEN_B64="$6"
ACCOUNT_B64="$7"

sudo -u "$USER" env \
  MOKLI_OANDA_TOKEN_B64="$TOKEN_B64" \
  MOKLI_OANDA_ACCOUNT_B64="$ACCOUNT_B64" \
  MOKLI_OANDA_ENV="$OANDA_ENV" \
  MOKLI_OANDA_MARKER="$MARKER" \
  MOKLI_INSTALL="$INSTALL" \
  python3 <<'PY'
import base64
import os
from pathlib import Path

token = base64.b64decode(os.environ["MOKLI_OANDA_TOKEN_B64"]).decode()
account = base64.b64decode(os.environ["MOKLI_OANDA_ACCOUNT_B64"]).decode()
oanda_env = os.environ.get("MOKLI_OANDA_ENV", "practice")
marker = os.environ["MOKLI_OANDA_MARKER"]
env_path = Path(os.environ["MOKLI_INSTALL"]) / ".env"

lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
out: list[str] = []
skip = False
for line in lines:
    if line.strip() == marker:
        skip = True
        continue
    if skip:
        if line.startswith("# ---") and line.strip() != marker:
            skip = False
            out.append(line)
        continue
    out.append(line)
while out and not out[-1].strip():
    out.pop()
if out and out[-1].strip():
    out.append("")
out.extend([
    marker,
    f"OANDA_API_TOKEN={token}",
    f"OANDA_ACCOUNT_ID={account}",
    f"OANDA_ENV={oanda_env}",
    "",
])
env_path.parent.mkdir(parents=True, exist_ok=True)
env_path.write_text("\n".join(out), encoding="utf-8")
try:
    env_path.chmod(0o600)
except OSError:
    pass
PY

sudo systemctl restart "$UNIT"
for _ in $(seq 1 15); do
  if curl -sf http://127.0.0.1:8766/api/v2/health >/dev/null 2>&1; then
    echo "OANDA_OK env_updated service=$UNIT"
    exit 0
  fi
  sleep 2
done
echo "OANDA_WARN gateway health not ready after restart" >&2
exit 1
EOS

echo "OK merged OANDA into ${INSTALL_DIR}/.env on VPS (secrets not logged)"
