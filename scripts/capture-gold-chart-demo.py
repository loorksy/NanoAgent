#!/usr/bin/env python3
"""Capture gold chart demo screenshot via Playwright."""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> int:
    out = Path("/opt/cursor/artifacts/screenshots/gold_chart_live_analysis.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    url = "http://127.0.0.1:8765/#/chart"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(url, wait_until="networkidle", timeout=60_000)

        page.wait_for_selector("h1:has-text('Gold Chart')", timeout=60_000)
        page.wait_for_timeout(3000)

        analyze_btn = page.get_by_role("button", name="Analyze gold")
        analyze_btn.click()

        page.wait_for_selector("text=Confidence:", timeout=120_000)
        page.wait_for_timeout(2000)

        page.screenshot(path=str(out), full_page=True)
        browser.close()

    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
