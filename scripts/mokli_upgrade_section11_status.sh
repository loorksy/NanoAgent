#!/usr/bin/env bash
# Print §11 artifact readiness (local or after vps_section11_pull_events.sh).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${ROOT}/.venv/bin/python"
[[ -x "$PYTHON" ]] || PYTHON=python3

SKIP_QUOTA=0
EVENTS="$ROOT/section11-events"
RESULTS="$ROOT/section11-results-partial.json"
REQUIRE=13

usage() {
  echo "Usage: $0 [--skip-quota] [--dir EVENTS] [--results JSON] [--require-through N]" >&2
  echo "  Legacy: $0 [EVENTS] [RESULTS] [REQUIRE]" >&2
  exit 2
}

POSITIONAL=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-quota) SKIP_QUOTA=1; shift ;;
    --dir) EVENTS="$2"; shift 2 ;;
    --results) RESULTS="$2"; shift 2 ;;
    --require-through) REQUIRE="$2"; shift 2 ;;
    -h | --help) usage ;;
    --*) echo "Unknown flag: $1" >&2; usage ;;
    *) POSITIONAL+=("$1"); shift ;;
  esac
done

if [[ ${#POSITIONAL[@]} -ge 1 ]]; then
  EVENTS="${POSITIONAL[0]}"
fi
if [[ ${#POSITIONAL[@]} -ge 2 ]]; then
  RESULTS="${POSITIONAL[1]}"
fi
if [[ ${#POSITIONAL[@]} -ge 3 ]]; then
  REQUIRE="${POSITIONAL[2]}"
fi

if [[ ! -f "$RESULTS" ]]; then
  echo "WARN: results file missing: $RESULTS (copy from docs/section11-results.example.json)" >&2
  exit 1
fi

echo "== §11 status (events=$EVENTS require-through=$REQUIRE) =="
VALIDATE_OK=0
if "$PYTHON" "${ROOT}/scripts/mokli_upgrade_section11_validate.py" \
  --dir "$EVENTS" --results "$RESULTS" --require-through "$REQUIRE"; then
  VALIDATE_OK=1
fi

QUOTA_OK=0
if [[ "$SKIP_QUOTA" -eq 1 ]]; then
  echo "== VPS LLM quota probe skipped (--skip-quota) =="
  QUOTA_OK=1
elif [[ -n "${MOKLI_SSH_HOST:-}" ]] || [[ -n "${VPS:-}" ]]; then
  echo "== VPS LLM quota probe =="
  if bash "${ROOT}/scripts/vps_section11_quota_probe.sh" "quota-status-$(date +%s).jsonl"; then
    QUOTA_OK=1
    echo "LLM: ready for live §11 turns"
  else
    echo "LLM: blocked (see operator handoff — credits or preset)"
  fi
else
  echo "== VPS LLM quota probe skipped (set MOKLI_SSH_HOST) =="
  QUOTA_OK=1
fi

if [[ "$VALIDATE_OK" -eq 1 && "$QUOTA_OK" -eq 1 ]]; then
  echo "OK §11 status: artifacts and LLM probe ready for require-through=$REQUIRE"
  exit 0
fi

echo "INCOMPLETE §11 status: validate_ok=$VALIDATE_OK quota_ok=$QUOTA_OK" >&2
exit 1
