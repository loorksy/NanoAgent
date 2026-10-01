#!/usr/bin/env bash
# Preflight before Mokli upgrade §11 live scenarios (report + operator handoff).
# Does not call the LLM or broker; checks API health and config readiness only.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fail=0

check_url() {
  local label="$1"
  local url="$2"
  if curl -sf --max-time 5 "$url" >/dev/null 2>&1; then
    echo "OK  $label"
  else
    echo "FAIL $label ($url)"
    fail=1
  fi
}

check_url "Agent API /api/v2/health" "http://127.0.0.1:8766/api/v2/health"

if curl -sf --max-time 5 "http://127.0.0.1:5173/api/v2/health" >/dev/null 2>&1; then
  echo "OK  Vite proxy /api/v2/health (5173 → backend)"
else
  echo "SKIP Vite proxy (5173 not running — start: cd mokli-ui && bun run dev --host 127.0.0.1 --port 5173)"
fi

PYTHON="${ROOT}/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON=python3
fi

"$PYTHON" <<'PY'
import json
import os
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

try:
    from mokli.config.loader import load_config

    cfg = load_config()
    oanda = cfg.trading_oanda.public_view()
    meta = cfg.trading_metaapi.public_view()
    if oanda.get("configured"):
        print(f"INFO OANDA configured (env={oanda.get('env')}, account_id set={bool(oanda.get('account_id'))})")
    else:
        print("WARN OANDA not configured — §11 rows 4/9/10 need candles (OANDA or warehouse fallback)")
    if meta.get("configured"):
        print("INFO MetaAPI token configured")
    else:
        print("WARN MetaAPI not configured — live quote paths may use OANDA only")
except Exception as exc:
    print(f"SKIP mokli config loader ({exc.__class__.__name__}) — check tradingOanda/tradingMetaapi manually")
    oanda_block = config.get("tradingOanda") or config.get("trading_oanda") or {}
    if isinstance(oanda_block, dict) and (oanda_block.get("apiToken") or oanda_block.get("api_token")):
        print("INFO OANDA apiToken present in config.json (not validated)")
    elif os.environ.get("OANDA_API_TOKEN") or os.environ.get("OANDA_API_KEY"):
        print("INFO OANDA token in environment")
    else:
        print("WARN no OANDA token in config.json or OANDA_* env")
PY

if [[ -x "${ROOT}/.venv/bin/pytest" ]]; then
  echo "INFO aggregate pytest (optional): pytest tests/agent tests/trading tests/agent_api \\"
  echo "  tests/deploy/test_mokli_pipe.py tests/scripts/ -q"
fi

if bash "${ROOT}/scripts/cloud_agent_vps_secrets_check.sh" >/dev/null 2>&1; then
  echo "OK  VPS deploy credentials (cloud_agent_vps_secrets_check)"
else
  echo "SKIP VPS deploy credentials — run: bash scripts/cloud_agent_vps_secrets_check.sh"
fi

echo "INFO §11 scaffold (VPS, no LLM): bash scripts/mokli_upgrade_section11_init.sh"
echo "INFO §11 toolchain dry-run (no LLM): bash scripts/mokli_upgrade_section11_dry_run.sh"
echo "INFO after each live turn: SHOW_DIAGNOSTICS on pipe → save JSONL →"
echo "  python scripts/mokli_upgrade_diagnostic_extract.py --file events.jsonl"
echo "  python scripts/mokli_upgrade_section11_batch.py --dir ./section11-events/ --results section11-results.json --markdown --require-through 13"
echo "  partial preview @10: mokli_upgrade_section11_close.sh --results section11-results-partial.json --require-through 10 --allow-partial"
echo "  bash scripts/mokli_upgrade_section11_validate.sh --dir ./section11-events/ --results section11-results.json"
echo "  python scripts/mokli_upgrade_section11_patch_report.py --dir ./section11-events/ --results section11-results.json --dry-run"
echo "  bash scripts/mokli_upgrade_section11_close.sh --apply  # after live §11 artifacts"
echo "INFO VPS closure chain (after quota + OANDA): bash scripts/mokli_upgrade_section11_timer_wake.sh --wait-quota"
echo "INFO VPS readiness gate: bash scripts/mokli_upgrade_section11_operator_unblock.sh --pull-vps"

exit "$fail"
