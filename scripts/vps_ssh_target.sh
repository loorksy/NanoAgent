#!/usr/bin/env bash
# Normalize Cloud Agent VPS secret into an ssh user@host target.
# Accepts: hostname, user@host, or "ssh user@host" command fragments.
normalize_vps_ssh_target() {
  local raw="${1:-}"
  raw="${raw#ssh }"
  raw="${raw#SSH }"
  raw="${raw#"${raw%%[![:space:]]*}"}"
  raw="${raw%"${raw##*[![:space:]]}"}"
  if [[ "$raw" == *@* ]]; then
    printf '%s\n' "$raw"
  else
    printf 'root@%s\n' "$raw"
  fi
}
