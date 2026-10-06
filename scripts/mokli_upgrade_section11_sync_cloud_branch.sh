#!/usr/bin/env bash
# Fast-forward Cloud Agent workspace to origin (§11 branch) before timer_wake / after_reset_wake.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BRANCH="${MOKLI_SECTION11_VPS_BRANCH:-cursor/section11-vps-rows-d9e1}"

if ! git -C "$ROOT" rev-parse --is-inside-work-tree &>/dev/null; then
  echo "CLOUD_PULL_SKIP=not_a_git_repo"
  exit 0
fi

echo "== Cloud Agent git ($BRANCH) =="
if ! git -C "$ROOT" fetch origin "$BRANCH" 2>&1; then
  echo "WARN: git fetch failed — continuing with current checkout" >&2
  echo "CLOUD_PULL_OK rev=$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo unknown)"
  exit 0
fi

git -C "$ROOT" checkout "$BRANCH" 2>/dev/null || true
if git -C "$ROOT" pull --ff-only origin "$BRANCH" 2>&1; then
  echo "CLOUD_PULL_OK rev=$(git -C "$ROOT" rev-parse --short HEAD)"
else
  echo "WARN: git pull --ff-only failed — continuing with current checkout" >&2
  echo "CLOUD_PULL_OK rev=$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo unknown)"
fi
