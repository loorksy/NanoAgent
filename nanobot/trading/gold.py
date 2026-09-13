"""Gold-only symbol guard — the platform's single instrument."""

from __future__ import annotations

DATA_SYMBOL = "XAUUSD"
OANDA_INSTRUMENT = "XAU_USD"
DISPLAY_NAME_EN = "Gold"


def display_name(locale: str | None = None) -> str:
    from nanobot.trading.i18n import tr

    return tr("display.gold", locale)


class GoldOnlyError(ValueError):
    """Raised when a non-gold symbol reaches a trading data path."""

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        super().__init__(
            f"This platform analyses gold ({DATA_SYMBOL}) only — "
            f'symbol "{symbol}" is not supported.'
        )


def _normalise(symbol: str) -> str:
    return symbol.replace("/", "").replace("_", "").replace("-", "").upper()[:6]


def is_gold(symbol: str | None) -> bool:
    if not symbol:
        return False
    return _normalise(symbol) == DATA_SYMBOL


def require_gold(symbol: str | None) -> str:
    if not is_gold(symbol):
        raise GoldOnlyError(str(symbol or ""))
    return DATA_SYMBOL


def coerce_to_gold(_symbol: str | None = None) -> str:
    return DATA_SYMBOL
