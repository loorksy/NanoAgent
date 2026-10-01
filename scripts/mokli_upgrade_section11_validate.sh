#!/usr/bin/env bash
# Wrapper for mokli_upgrade_section11_validate.py (uses repo .venv when present).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${ROOT}/.venv/bin/python"
[[ -x "$PYTHON" ]] || PYTHON=python3
exec "$PYTHON" "${ROOT}/scripts/mokli_upgrade_section11_validate.py" "$@"
