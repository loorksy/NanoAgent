
import pytest

from nanobot.trading.chart_host_token import (
    mint_chart_host_page_token,
    verify_chart_host_page_token,
)


@pytest.fixture(autouse=True)
def chart_host_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NANOBOT_CHART_HOST_TOKEN", "test-chart-host-secret-123456")


def test_chart_host_token_roundtrip() -> None:
    token = mint_chart_host_page_token(ttl_sec=120)
    assert token
    assert verify_chart_host_page_token(token)


def test_chart_host_token_rejects_tampered() -> None:
    token = mint_chart_host_page_token(ttl_sec=120)
    assert token
    assert not verify_chart_host_page_token(f"{token}tampered")


def test_chart_host_token_requires_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NANOBOT_CHART_HOST_TOKEN", raising=False)
    assert mint_chart_host_page_token() is None
