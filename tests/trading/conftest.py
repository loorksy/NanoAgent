"""Isolate trading gate tests from the operator's ~/.nanobot/config.json."""

from __future__ import annotations

import pytest

from nanobot.trading.policy import invalidate_live_cache


@pytest.fixture(autouse=True)
def _isolate_trading_config(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("nanobot.config.loader._current_config_path", tmp_path / "config.json")
    invalidate_live_cache()
    yield
    invalidate_live_cache()
