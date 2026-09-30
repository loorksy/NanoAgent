#!/usr/bin/env bash
# Preflight before Mokli upgrade §11 live scenarios (report + operator handoff).
# Does not call the LLM or broker; checks API health and config readiness only.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fail=0

check_url() {
  local label="$1"
  local url="$2"
  if curl -sf "$url" >/dev/null 2>&1; then
    echo "OK  $label"
  else
    echo "FAIL $label ($url)"
    fail=1
  fi
}

check_url "Agent API /api/v2/health" "http://127.0.0.1:8766/api/v2/health"

if curl -sf "http://127.0.0.1:5173/api/v2/health" >/dev/null 2>&1; then
  echo "OK  Vite proxy /api/v2/health (5173 → backend)"
else
  echo "SKIP Vite proxy (5173 not running — start: cd mokli-ui && bun run dev --host 127.0.0.1 --port 5173)"
fi

python3 <<'PY'
import json
import sys
from pathlib import Path

config_path = Path.home() / ".mokli/config.json"
if not config_path.exists():
    print("WARN no ~/.mokli/config.json — configure provider before §11 rows 1–9")
    sys.exit(0)

config = json.loads(config_path.read_text())
defaults = config.get("agents", {}).get("defaults", {})
model = defaults.get("model") or defaults.get("modelPreset") or "(unset)"
print(f"INFO default model: {model}")

providers = config.get("providers") or {}
has_key = False
for name, block in providers.items():
    if not isinstance(block, dict):
        continue
    key = block.get("apiKey")
    if isinstance(key, str) and key.strip():
        has_key = True
        print(f"INFO provider with apiKey set: {name}")
        break

if not has_key:
    print("WARN all provider apiKey fields empty — §11 chat paths need LLM credentials")
PY

if [[ -x "${ROOT}/.venv/bin/pytest" ]]; then
  echo "INFO aggregate pytest (optional): pytest tests/agent tests/trading tests/agent_api \\"
  echo "  tests/deploy/test_mokli_pipe.py tests/scripts/test_mokli_upgrade_diagnostic_extract.py \\"
  echo "  tests/scripts/test_mokli_upgrade_preflight.py -q"
fi

echo "INFO after each live turn: SHOW_DIAGNOSTICS on pipe → save JSONL →"
echo "  python scripts/mokli_upgrade_diagnostic_extract.py --file events.jsonl"

exit "$fail"
