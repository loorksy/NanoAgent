# Deploying Mokli against a self-hosted MT5 terminal

Mokli does not embed a trading terminal and does not call a cloud broker. It expects a MetaTrader 5 terminal that is **already running** and reachable at `MT5_HOST:MT5_PORT` through the [mt5linux](https://pypi.org/project/mt5linux/) RPyC bridge (the 0.2.x client).

That terminal can be:

- the Hostinger MetaTrader 5 Docker template, or
- any Wine-based MT5 container that exposes the mt5linux bridge port.

No other broker-side setup is required. Copying this project to another VPS only needs the environment variables below. Do not hardcode a host, port, login, password, or server name.

## Bridge package

Install the trading extra from this repo:

```bash
pip install '.[trading-mt5]'
```

`trading-mt5` depends on `mt5linux>=0.2.4,<1`. That release is a client: `MetaTrader5(host, port)` dials an existing bridge. The 1.x line starts its own container and is intentionally not used here.

## Environment

Copy `.env.example` to `.env` (gitignored) and set:

| Variable | Required | Default | Meaning |
| --- | --- | --- | --- |
| `MT5_HOST` | no | `localhost` | Bridge host. Use a container or VPS hostname when Mokli and MT5 are not on the same network namespace. |
| `MT5_PORT` | no | `8001` | Bridge port published by the MT5 container. |
| `MT5_LOGIN` | yes | | MT5 account number. |
| `MT5_PASSWORD` | yes | | Trading password. Never commit it. |
| `MT5_SERVER` | yes | | Broker server name, as shown in the MT5 terminal. |
| `MT5_SYMBOL` | no | `XAUUSD` | Symbol printed by the connectivity script. |
| `MT5_DEVIATION` | no | `20` | Maximum price deviation (points) on market orders. |
| `MT5_TIMEOUT` | no | `10` | Seconds to wait for the bridge TCP port. |

`localhost` is only the default. If the agent and the MT5 container run on different hosts, set `MT5_HOST` to the address that reaches the bridge.

When these variables are set, they override credentials saved from the Connect screen. Clear `MT5_LOGIN`, `MT5_PASSWORD`, and `MT5_SERVER` on the server before using the form to disconnect or replace the account.

The Connect screen stores the password in the encrypted secret store (`mt5_password` inside `secrets.enc`). It is not written to `config.json` and it is not returned by the API.

## Check the link

From the repo root, with the variables exported:

```bash
python scripts/test_mt5_connection.py
```

A working bridge prints the account login, name, and balance, then one bid/ask for `MT5_SYMBOL`, and exits 0. A failure prints a redacted reason on stderr and exits 1.
