"""Broker-neutral trading surface.

Trading code talks to this interface. It does not import a broker SDK.
"""

from __future__ import annotations

from typing import Any, Protocol


class Broker(Protocol):
    """Connection and order verbs shared by every broker backend."""

    async def connect(self) -> dict[str, Any]:
        """Open the session. ``ok`` is false when the terminal cannot be reached."""

    async def get_account_info(self) -> dict[str, Any]:
        """Return ``{ok, account}`` with operator-safe account fields."""

    async def get_symbol_price(self, symbol: str) -> dict[str, Any]:
        """Return ``{ok, symbol, bid, ask, time}`` for one live quote."""

    async def get_candles(
        self, symbol: str, timeframe: str, count: int
    ) -> list[dict[str, Any]]:
        """Return up to ``count`` recent bars, oldest first when the terminal does."""

    async def place_order(
        self,
        *,
        symbol: str,
        side: str,
        lot: float,
        stop: float | None = None,
        take_profit: float | None = None,
        comment: str = "",
        kind: str = "market",
        price: float | None = None,
    ) -> dict[str, Any]:
        """Send a market or pending order. The result uses the shared broker envelope."""

    async def close_order(
        self,
        *,
        position_id: str | None = None,
        order_id: str | None = None,
        volume: float | None = None,
    ) -> dict[str, Any]:
        """Close a position, partially close it, or cancel a pending order."""

    async def get_open_positions(self) -> list[dict[str, Any]]:
        """Return open positions in the shape the execution layer already reads."""
