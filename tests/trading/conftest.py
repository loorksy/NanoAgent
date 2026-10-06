"""Isolate trading gate tests from the operator's ~/.mokli/config.json."""

from __future__ import annotations

import pytest

from mokli.trading.policy import invalidate_live_cache


@pytest.fixture(autouse=True)
def _isolate_trading_config(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("mokli.config.loader._current_config_path", tmp_path / "config.json")
    invalidate_live_cache()
    yield
    invalidate_live_cache()
