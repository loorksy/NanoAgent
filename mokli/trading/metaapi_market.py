"""Live gold quote from MetaAPI Cloud.

Historical candles stay on OANDA. This module only reads the current price.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import httpx

from mokli.trading.config import TradingConfig, load_trading_config
from mokli.trading.gold import DATA_SYMBOL, require_gold
from mokli.trading.oanda import OandaQuote

logger = logging.getLogger(__name__)

REGIONS = ("new-york", "london", "singapore", "amsterdam")


def client_api_base(region: str | None) -> str:
    name = region if region in REGIONS else "new-york"
    return f"https://mt-client-api-v1.{name}.agiliumtrade.ai"


def fetch_metaapi_quote(
    symbol: str,
    *,
    config: TradingConfig | None = None,
) -> OandaQuote | None:
    """Bid/ask for gold from the linked MetaAPI account."""
    config = config or load_trading_config()
    if getattr(config, "metaapi_configured", False) is not True:
        return None
    require_gold(symbol)
    account = config.metaapi_account_id
    token = config.metaapi_token
    if not account or not token:
        return None
    url = (
        f"{client_api_base(config.metaapi_region)}"
        f"/users/current/accounts/{account}/symbols/{DATA_SYMBOL}/current-price"
    )
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(
                url,
                headers={"auth-token": token, "Accept": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
    except Exception:
        logger.warning("MetaAPI quote failed")
        return None
    if not isinstance(data, dict):
        return None
    bid = _num(data.get("bid"))
    ask = _num(data.get("ask"))
    if bid is None or ask is None:
        return None
    return OandaQuote(
        symbol=DATA_SYMBOL,
        bid=bid,
        ask=ask,
        mid=(bid + ask) / 2,
        tradeable=True,
        quoted_at=_quoted_at(data.get("time")),
    )


def _quoted_at(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def quote_time_seconds(quoted_at: str | None) -> int | None:
    if not quoted_at:
        return None
    text = quoted_at[:-1] + "+00:00" if quoted_at.endswith("Z") else quoted_at
    try:
        return int(datetime.fromisoformat(text).timestamp())
    except ValueError:
        return None


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number <= 0:
        return None
    return number
