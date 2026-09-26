"""The vendored Open WebUI tree exposes the NanoAgent surfaces from design 04."""

from __future__ import annotations

import json
import re
from pathlib import Path

from aiohttp import web

from nanobot.agent_api.routes.jobs import register

ROOT = Path(__file__).resolve().parents[2]
ARABIC = re.compile(r"[\u0600-\u06FF]")

PAGES = (
    "open-webui/src/routes/(app)/tasks/+page.svelte",
    "open-webui/src/routes/(app)/recommendations/+page.svelte",
    "open-webui/src/routes/(app)/connect/+page.svelte",
    "open-webui/src/routes/(app)/log/+page.svelte",
)

SVELTE_ROOTS = (
    "open-webui/src/lib/components/nanoagent",
    "open-webui/src/lib/nanoagent",
    "open-webui/src/routes/(app)/tasks",
    "open-webui/src/routes/(app)/recommendations",
    "open-webui/src/routes/(app)/connect",
    "open-webui/src/routes/(app)/log",
)


def test_fork_pages_proxy_and_sidebar() -> None:
    for relative in PAGES:
        assert (ROOT / relative).is_file(), relative
    main = (ROOT / "open-webui/backend/open_webui/main.py").read_text(encoding="utf-8")
    assert "nanoagent," in main
    assert "prefix='/api/v1/nanoagent'" in main
    sidebar = (ROOT / "open-webui/src/lib/components/layout/Sidebar.svelte").read_text(
        encoding="utf-8"
    )
    assert "NanoAgentNav" in sidebar
    assert "nanoagent-chart-button" in (
        ROOT / "open-webui/src/lib/components/chat/MessageInput.svelte"
    ).read_text(encoding="utf-8")
    assert "nanoagent-claude-connect" in (
        ROOT / "open-webui/src/lib/components/nanoagent/NanoAgentProviders.svelte"
    ).read_text(encoding="utf-8")
    assert "no-cache, no-store, must-revalidate" in main
    brands = (ROOT / "open-webui/src/lib/nanoagent/provider-brand.ts").read_text(encoding="utf-8")
    assert "claude_code_cli: 'anthropic'" in brands
    assert "openrouter:" in brands
    assert "anthropic:" in brands
    assert (ROOT / "open-webui/src/routes/(app)/workspace/agent/+page.svelte").is_file()
    assert "__nanoagent_macro__" in (
        ROOT / "open-webui/src/routes/(app)/calendar/+page.svelte"
    ).read_text(encoding="utf-8")
    settings = (ROOT / "open-webui/src/lib/components/chat/SettingsModal.svelte").read_text(
        encoding="utf-8"
    )
    assert "NanoAgentSettings" in settings
    assert "nanoagent:" in settings
    compose = (ROOT / "deploy/openwebui/docker-compose.yml").read_text(encoding="utf-8")
    assert "context: ../../open-webui" in compose
    assert "NANOAGENT_GATEWAY_URL" in compose
    english = json.loads(
        (ROOT / "open-webui/src/lib/nanoagent/i18n/en.json").read_text(encoding="utf-8")
    )
    arabic = json.loads(
        (ROOT / "open-webui/src/lib/nanoagent/i18n/ar.json").read_text(encoding="utf-8")
    )
    assert set(english) == set(arabic)


def test_fork_svelte_keeps_arabic_in_json_only() -> None:
    offenders: list[str] = []
    for relative in SVELTE_ROOTS:
        root = ROOT / relative
        for path in root.rglob("*"):
            if path.suffix not in {".svelte", ".ts"}:
                continue
            if ARABIC.search(path.read_text(encoding="utf-8")):
                offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_tasks_alias_matches_jobs() -> None:
    app = web.Application()
    register(app.router, "/api/v2")
    paths = {route.resource.canonical for route in app.router.routes() if route.resource}
    assert "/api/v2/tasks" in paths
    assert "/api/v2/tasks/{id}/cancel" in paths
    assert "/api/v2/jobs/{id}/pause" in paths
