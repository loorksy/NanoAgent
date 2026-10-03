#!/usr/bin/env bash
# The installers must skip a healthy bridge and must not print secrets or the
# container address. A fake docker stands in for the live MT5 container.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

bash -n "$ROOT/scripts/install-nanoagent-host.sh"
bash -n "$ROOT/scripts/install-mt5linux-bridge.sh"
bash -n "$ROOT/scripts/install-mt5linux-shim.sh"

make_docker() {
  local bin="$1"
  cat >"$bin" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"${DOCKER_LOG:?}"
if [[ "$1" == "inspect" ]]; then
  if [[ "${DOCKER_RUNNING:-1}" == 0 ]]; then
    printf 'false\n'
    exit 0
  fi
  if [[ "$*" == *IPAddress* ]]; then
    printf '%s \n' "${DOCKER_IP:?}"
    exit 0
  fi
  printf 'true\n'
  exit 0
fi
if [[ "$1" == "exec" ]]; then
  if [[ "$*" == *MetaTrader5* && "${FAIL_WINE:-0}" == 1 ]]; then
    exit 1
  fi
  if [[ "$*" == *mt5linux.__file__* ]]; then
    printf '%s\n' "/config/.local/lib/python3.11/site-packages/mt5linux/__main__.py"
    exit 0
  fi
  exit 0
fi
if [[ "$1" == "cp" ]]; then
  printf 'docker cp was not expected\n' >&2
  exit 1
fi
printf 'unexpected docker %s\n' "$*" >&2
exit 1
EOF
  chmod 0755 "$bin"
}

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
make_docker "$work/docker"

export DOCKER_LOG="$work/docker.log"
export DOCKER_IP="203.0.113.10"
export PATH="$work:${PATH}"
: >"$DOCKER_LOG"

out="$(MT5_CONTAINER=fake-mt5 bash "$ROOT/scripts/install-mt5linux-bridge.sh")"
printf '%s\n' "$out" | grep -q "pinned packages already installed" || fail "healthy bridge was not skipped"
if printf '%s\n' "$out" | grep -q "would install"; then
  fail "healthy bridge wanted an install"
fi
if grep -q '^cp ' "$DOCKER_LOG"; then
  fail "healthy bridge copied a file"
fi

: >"$DOCKER_LOG"
export FAIL_WINE=1
out="$(NANOAGENT_BRIDGE_DRY_RUN=1 MT5_CONTAINER=fake-mt5 bash "$ROOT/scripts/install-mt5linux-bridge.sh")"
printf '%s\n' "$out" | grep -q "would install 64-bit Python 3.11.9" || fail "dry run did not describe the install"
if grep -q '^cp ' "$DOCKER_LOG"; then
  fail "dry run copied a file"
fi
unset FAIL_WINE

: >"$DOCKER_LOG"
export DOCKER_RUNNING=0
out="$(MT5_CONTAINER=fake-mt5 bash "$ROOT/scripts/install-mt5linux-bridge.sh" 2>&1)"
printf '%s\n' "$out" | grep -q "not running; skipped" || fail "stopped container was not skipped"
unset DOCKER_RUNNING

# shellcheck disable=SC1091
NANOAGENT_INSTALL_LIB_ONLY=1 source "$ROOT/scripts/install-nanoagent-host.sh"

envfile="$work/.env"
printf 'MT5_HOST=localhost\nOANDA_API_TOKEN=kept-secret\n' >"$envfile"
export DOCKER_IP="203.0.113.10"
wire_out="$(MT5_CONTAINER=fake-mt5 wire_mt5_host "$envfile")"
grep -q '^MT5_HOST=203.0.113.10$' "$envfile" || fail "localhost was not replaced"
grep -q '^OANDA_API_TOKEN=kept-secret$' "$envfile" || fail "existing env value changed"
if printf '%s\n' "$wire_out" | grep -q '203.0.113.10'; then
  fail "container address was printed"
fi
if printf '%s\n' "$wire_out" | grep -q 'kept-secret'; then
  fail "secret was printed"
fi
printf '%s\n' "$wire_out" | grep -q "address was not printed" || fail "wire result was not reported"

printf 'MT5_HOST=192.0.2.20\n' >"$envfile"
wire_mt5_host "$envfile" >/dev/null
grep -q '^MT5_HOST=192.0.2.20$' "$envfile" || fail "custom MT5_HOST was overwritten"

secretfile="$work/mokli-ui.env"
printf 'MOKLI_SECRET_KEY=not-shown\nMOKLI_API_TOKEN=\nMT5_DESKTOP_PASSWORD=\n' >"$secretfile"
report="$(report_blank_keys "$secretfile" "set these keys" MOKLI_SECRET_KEY MOKLI_API_TOKEN MT5_DESKTOP_PASSWORD)"
printf '%s\n' "$report" | grep -q 'MOKLI_API_TOKEN' || fail "blank token was not listed"
printf '%s\n' "$report" | grep -q 'MT5_DESKTOP_PASSWORD' || fail "blank desktop password was not listed"
if printf '%s\n' "$report" | grep -q 'MOKLI_SECRET_KEY'; then
  fail "filled key was listed"
fi
if printf '%s\n' "$report" | grep -q 'not-shown'; then
  fail "secret value was printed"
fi

printf 'ok\n'
