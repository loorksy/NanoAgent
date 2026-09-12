from nanobot.trading.news.forex_factory import fetch_upcoming_events


def test_forex_factory_disabled_by_default() -> None:
    assert fetch_upcoming_events() == []
