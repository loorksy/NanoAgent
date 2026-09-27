"""Confirm the self-hosted MT5 bridge after a redeploy.

Reads MT5_HOST, MT5_PORT, MT5_LOGIN, MT5_PASSWORD, and MT5_SERVER from the
environment (saved operator credentials are used only when a variable is unset).
Prints the account balance and one live price, then exits.
"""

from __future__ import annotations

import asyncio
import os
import sys

from mokli.trading.mt5_broker import Mt5LinuxBroker


async def main() -> int:
    symbol = (os.environ.get("MT5_SYMBOL") or "XAUUSD").strip() or "XAUUSD"
    broker = Mt5LinuxBroker.from_env()
    connected = await broker.connect()
    if not connected.get("ok"):
        print(f"connect failed: {connected.get('error')}", file=sys.stderr)
        return 1
    info = await broker.get_account_info()
    if not info.get("ok"):
        print(f"account failed: {info.get('error')}", file=sys.stderr)
        return 1
    account = info.get("account") if isinstance(info.get("account"), dict) else {}
    print(
        "login={login} name={name} balance={balance} {currency}".format(
            login=account.get("login"),
            name=account.get("name"),
            balance=account.get("balance"),
            currency=account.get("currency") or "",
        )
    )
    price = await broker.get_symbol_price(symbol)
    if not price.get("ok"):
        print(f"price failed: {price.get('error')}", file=sys.stderr)
        return 1
    print(f"{symbol} bid={price.get('bid')} ask={price.get('ask')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
