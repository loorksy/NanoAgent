
from nanobot.trading.gates.news_policy import news_gate_mode


def test_news_gate_mode_defaults_to_warn(monkeypatch) -> None:
    monkeypatch.delenv("LONORA_NEWS_GATE_MODE", raising=False)
    assert news_gate_mode() == "warn"


def test_news_gate_mode_strict(monkeypatch) -> None:
    monkeypatch.setenv("LONORA_NEWS_GATE_MODE", "strict")
    assert news_gate_mode() == "strict"


def test_news_gate_mode_off(monkeypatch) -> None:
    monkeypatch.setenv("LONORA_NEWS_GATE_MODE", "off")
    assert news_gate_mode() == "off"
