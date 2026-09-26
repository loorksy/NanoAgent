#!/usr/bin/env bash
# Run the same checks as the CI "latest + coverage" Python job (local parity).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required; see https://docs.astral.sh/uv/" >&2
  exit 1
fi

uv sync --all-extras --dev
uv run --no-sync python -m scripts.install_channel_dependencies --all-channels
uv pip check

uv run --no-sync ruff check mokli tests conftest.py
uv run --no-sync basedpyright

PYTEST_ARGS=(-n auto --dist loadfile --ignore=tests/cli/test_commands.py)
uv run --no-sync python -m pytest "${PYTEST_ARGS[@]}" \
  --cov=mokli --cov-report=term-missing:skip-covered \
  --durations=25 --durations-min=1.0
uv run --no-sync python -m pytest tests/cli/test_commands.py \
  --cov=mokli --cov-append --cov-report=term-missing:skip-covered \
  --durations=25 --durations-min=1.0

echo "Local CI parity checks finished successfully."
