from nanobot.trading.gold import DATA_SYMBOL, GoldOnlyError, coerce_to_gold, is_gold, require_gold


def test_is_gold_accepts_aliases() -> None:
    assert is_gold("XAUUSD")
    assert is_gold("xau/usd")
    assert is_gold("XAU_USD")


def test_require_gold_rejects_other_symbols() -> None:
    try:
        require_gold("EURUSD")
    except GoldOnlyError as exc:
        assert exc.symbol == "EURUSD"
    else:
        raise AssertionError("expected GoldOnlyError")


def test_coerce_to_gold_always_returns_canonical() -> None:
    assert coerce_to_gold("EURUSD") == DATA_SYMBOL
