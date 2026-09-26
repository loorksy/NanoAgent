"""The public legacy React client is gone; chart assets and APIs stay."""

from __future__ import annotations

import inspect
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_public_proxy_does_not_route_the_legacy_client() -> None:
    caddy = (ROOT / "deploy/mokliui/Caddyfile").read_text(encoding="utf-8")
    compose = (ROOT / "deploy/mokliui/docker-compose.yml").read_text(encoding="utf-8")
    example = (ROOT / "deploy/mokliui/.env.example").read_text(encoding="utf-8")
    assert "/legacy" not in caddy
    assert "LEGACY_MOKLI_UPSTREAM" not in caddy
    assert "LEGACY_MOKLI_UPSTREAM" not in compose
    assert "LEGACY_MOKLI_UPSTREAM" not in example


def test_legacy_react_app_is_removed_and_charts_remain() -> None:
    assert not (ROOT / "mokli/package.json").is_file()
    assert not (ROOT / "mokli/src").exists()
    chart = ROOT / "mokli/public/charting_library/charting_library.standalone.js"
    assert chart.is_file()


def test_gateway_does_not_serve_the_legacy_spa_by_default() -> None:
    from mokli.cli.gateway_runtime import _run_gateway

    default = inspect.signature(_run_gateway).parameters["mokli_static_dist"].default
    assert default is False
