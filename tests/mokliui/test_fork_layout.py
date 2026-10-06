"""The vendored Mokli tree exposes the Mokli surfaces from design 04."""

from __future__ import annotations

import json
import re
from pathlib import Path

from aiohttp import web

from mokli.agent_api.routes.jobs import register

ROOT = Path(__file__).resolve().parents[2]
ARABIC = re.compile(r"[\u0600-\u06FF]")

PAGES = (
    "mokli-ui/src/routes/(app)/tasks/+page.svelte",
    "mokli-ui/src/routes/(app)/recommendations/+page.svelte",
    "mokli-ui/src/routes/(app)/connect/+page.svelte",
    "mokli-ui/src/routes/(app)/log/+page.svelte",
    "mokli-ui/src/routes/(app)/briefing/+page.svelte",
    "mokli-ui/src/routes/(app)/performance/+page.svelte",
    "mokli-ui/src/routes/(app)/usage/+page.svelte",
)

SVELTE_ROOTS = (
    "mokli-ui/src/lib/components/mokli",
    "mokli-ui/src/lib/mokli",
    "mokli-ui/src/routes/(app)/tasks",
    "mokli-ui/src/routes/(app)/recommendations",
    "mokli-ui/src/routes/(app)/connect",
    "mokli-ui/src/routes/(app)/log",
    "mokli-ui/src/routes/(app)/briefing",
    "mokli-ui/src/routes/(app)/performance",
    "mokli-ui/src/routes/(app)/usage",
)


def test_fork_pages_proxy_and_sidebar() -> None:
    for relative in PAGES:
        assert (ROOT / relative).is_file(), relative
    main = (ROOT / "mokli-ui/backend/mokli_ui/main.py").read_text(encoding="utf-8")
    assert "mokli," in main
    assert "prefix='/api/v1/mokli'" in main
    sidebar = (ROOT / "mokli-ui/src/lib/components/layout/Sidebar.svelte").read_text(
        encoding="utf-8"
    )
    assert "MokliNav" in sidebar
    nav = (ROOT / "mokli-ui/src/lib/components/mokli/MokliNav.svelte").read_text(
        encoding="utf-8"
    )
    for href in ("/briefing", "/performance", "/usage"):
        assert href in nav
    assert "onSelect" in nav
    assert "itemClickHandler" in sidebar
    assert "sidebar-operator" in sidebar
    section = (ROOT / "mokli-ui/src/lib/components/layout/Sidebar/Section.svelte").read_text(
        encoding="utf-8"
    )
    assert 'd="M4 7h16M4 12h16M4 17h16"' in section
    assert "mokli-chart-button" in (
        ROOT / "mokli-ui/src/lib/components/chat/MessageInput.svelte"
    ).read_text(encoding="utf-8")
    assert "mokli-claude-connect" in (
        ROOT / "mokli-ui/src/lib/components/mokli/MokliProviders.svelte"
    ).read_text(encoding="utf-8")
    assert "no-cache, no-store, must-revalidate" in main
    brands = (ROOT / "mokli-ui/src/lib/mokli/provider-brand.ts").read_text(encoding="utf-8")
    assert "claude_code_cli: 'anthropic'" in brands
    assert "openrouter:" in brands
    assert "anthropic:" in brands
    assert (ROOT / "mokli-ui/src/routes/(app)/workspace/agent/+page.svelte").is_file()
    assert "__mokli_macro__" in (
        ROOT / "mokli-ui/src/routes/(app)/calendar/+page.svelte"
    ).read_text(encoding="utf-8")
    settings = (ROOT / "mokli-ui/src/lib/components/chat/SettingsModal.svelte").read_text(
        encoding="utf-8"
    )
    assert "MokliSettings" in settings
    assert "mokli:" in settings
    compose = (ROOT / "deploy/mokliui/docker-compose.yml").read_text(encoding="utf-8")
    assert "context: ../../mokli-ui" in compose
    assert "MOKLI_GATEWAY_URL" in compose
    english = json.loads(
        (ROOT / "mokli-ui/src/lib/mokli/i18n/en.json").read_text(encoding="utf-8")
    )
    arabic = json.loads(
        (ROOT / "mokli-ui/src/lib/mokli/i18n/ar.json").read_text(encoding="utf-8")
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
