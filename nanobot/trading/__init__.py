"""Gold (XAUUSD) trading recommendation runtime."""

from nanobot.trading.gold import DATA_SYMBOL, GoldOnlyError, coerce_to_gold, is_gold, require_gold

__all__ = [
    "DATA_SYMBOL",
    "GoldOnlyError",
    "coerce_to_gold",
    "is_gold",
    "require_gold",
]
