#!/usr/bin/env bash
# Map Cloud Agent / dashboard secret names to deploy script variables.
# Preferred: VPS (host or user@host) and VPSPASS (SSH password).
# Also accepts lowercase vps and password when the dashboard uses those names.
set -euo pipefail

if [[ -z "${VPS:-}" && -n "${vps:-}" ]]; then
  export VPS="$vps"
fi
if [[ -z "${VPSPASS:-}" && -n "${password:-}" ]]; then
  export VPSPASS="$password"
fi
