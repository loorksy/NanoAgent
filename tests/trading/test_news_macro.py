from nanobot.trading.agents.news_macro import news_provider_configured, run_news_macro_agent


def test_news_provider_requires_forex_factory_flag(monkeypatch) -> None:
    monkeypatch.delenv("FOREX_FACTORY_ENABLED", raising=False)
    monkeypatch.delenv("TRADING_NEWS_STUB", raising=False)
    assert news_provider_configured() is False


def test_news_macro_unconfigured_returns_unknown(monkeypatch) -> None:
    monkeypatch.delenv("FOREX_FACTORY_ENABLED", raising=False)
    result = run_news_macro_agent()
    assert result.news_risk == "unknown"
    assert result.trade_allowed is False
    assert "FOREX_FACTORY_ENABLED" in result.reason


def test_news_macro_live_empty_calendar(monkeypatch) -> None:
    monkeypatch.setenv("FOREX_FACTORY_ENABLED", "1")
    monkeypatch.setattr(
        "nanobot.trading.agents.news_macro.fetch_upcoming_events",
        lambda: [],
    )
    result = run_news_macro_agent()
    assert result.news_risk == "low"
    assert result.trade_allowed is True
