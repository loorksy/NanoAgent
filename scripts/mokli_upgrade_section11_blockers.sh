#!/usr/bin/env bash
# One-page §11 production blockers: VPS env + validate through 13 (exit 1 if not closable).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${ROOT}/.venv/bin/python"
[[ -x "$PYTHON" ]] || PYTHON=python3
EVENTS="${1:-$ROOT/section11-events}"
RESULTS="${2:-$ROOT/section11-results-partial.json}"

ENV_OK=0
echo "== VPS env (quota + OANDA required for full closure) =="
if bash "$ROOT/scripts/vps_section11_env_check.sh" --require-quota --require-oanda; then
  ENV_OK=1
fi

echo ""
echo "== §11 artifacts (require-through 13) =="
VAL_OK=0
if "$PYTHON" "$ROOT/scripts/mokli_upgrade_section11_validate.py" \
  --dir "$EVENTS" --results "$RESULTS" --require-through 13; then
  VAL_OK=1
fi

echo ""
if [[ "$ENV_OK" -eq 1 && "$VAL_OK" -eq 1 ]]; then
  echo "OK §11 blockers clear — run mokli_upgrade_section11_close.sh --apply --require-through 13"
  exit 0
fi

echo "BLOCKED §11 production closure (env_ok=$ENV_OK validate_ok=$VAL_OK)" >&2
echo "See: docs/mokli-agent-upgrade-operator-handoff.md" >&2
echo "Quick reruns when quota returns: bash scripts/mokli_upgrade_section11_rerun_partials.sh" >&2
exit 1
