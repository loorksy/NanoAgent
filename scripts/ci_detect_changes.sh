#!/usr/bin/env bash
# Classify which CI jobs are required for the current GitHub event.
set -euo pipefail

python_required=true
mokli_required=true
tui_required=true
docker_required=true

event_name="${GITHUB_EVENT_NAME:-${EVENT_NAME:-}}"

if [[ "$event_name" == "pull_request" ]]; then
  base_sha="${PR_BASE_SHA:-}"
  head_sha="${PR_HEAD_SHA:-${GITHUB_SHA:-}}"
  diff_range="${base_sha}...${head_sha}"
elif [[ "$event_name" == "push" ]]; then
  base_sha="${BASE_SHA:-}"
  head_sha="${HEAD_SHA:-${GITHUB_SHA:-}}"
  if [[ -z "$base_sha" || "$base_sha" == "0000000000000000000000000000000000000000" ]] ||
    ! git cat-file -e "${base_sha}^{commit}" 2>/dev/null; then
    base_sha="$(git rev-parse "${head_sha}^" 2>/dev/null || true)"
  fi
  diff_range="${base_sha}..${head_sha}"
else
  diff_range="${head_sha}~1..${head_sha}"
fi

if [[ -n "$base_sha" ]] && git cat-file -e "${base_sha}^{commit}" 2>/dev/null; then
  changed_files="$(git diff --name-only --no-renames "$diff_range" || true)"
  if [[ -n "$changed_files" ]]; then
    python_required=false
    mokli_required=false
    tui_required=false
    docker_required=false

    while IFS= read -r file || [[ -n "$file" ]]; do
      [[ -z "$file" ]] && continue
      case "$file" in
        .github/workflows/*)
          python_required=true
          mokli_required=true
          tui_required=true
          docker_required=true
          ;;
        mokli/*|mokli-ui/*|mokli/channels/*/mokli/*)
          mokli_required=true
          docker_required=true
          ;;
        mokli/*)
          python_required=true
          docker_required=true
          ;;
        tests/test_docker.sh)
          docker_required=true
          ;;
        pyproject.toml|hatch_build.py|scripts/install_channel_dependencies.py)
          python_required=true
          docker_required=true
          ;;
        tests/*|conftest.py|uv.lock|scripts/*)
          python_required=true
          ;;
        Dockerfile|Dockerfile.*|.dockerignore|docker-compose*.yml|entrypoint.sh|render-config.json|README.md|LICENSE|THIRD_PARTY_NOTICES.md)
          docker_required=true
          ;;
        tui/*)
          tui_required=true
          ;;
        docs/*|.agent/*|.github/ISSUE_TEMPLATE/*|AGENTS.md|CLAUDE.md|COMMUNICATION.md|CONTRIBUTING.md|README.md|SECURITY.md|mokli/README.md|render.yaml)
          ;;
        *)
          python_required=true
          mokli_required=true
          tui_required=true
          docker_required=true
          ;;
      esac
    done <<< "$changed_files"
  fi
fi

{
  echo "python_required=$python_required"
  echo "mokli_required=$mokli_required"
  echo "tui_required=$tui_required"
  echo "docker_required=$docker_required"
} >> "${GITHUB_OUTPUT}"
