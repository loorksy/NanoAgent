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

## Hostinger image: mt5linux 1.1.1 does not start

The Hostinger MetaTrader 5 template runs `gmag11/metatrader5_vnc` and launches the bridge once from `/Metatrader/start.sh`:

```bash
python3 -m mt5linux --host 0.0.0.0 -p 8001 -w wine python.exe
```

That image installs **mt5linux 1.1.1**. Importing it raises `SyntaxError` in `metatrader5.py`, so the process exits and port 8001 never listens. Nothing in the image supervises that process: s6 watches the desktop, not the bridge.

The working server is the same 0.2.x line as the client in `trading-mt5` (0.2.4). It has to run under Wine, because that is the interpreter that can `import MetaTrader5`. On the container volume mounted at `/config`:

- Linux and Wine `mt5linux` are pinned to 0.2.4, with `rpyc` 5.2.3.
- Wine `numpy` stays on 1.26.4. NumPy 2 cannot load the MetaTrader5 extension shipped in the image.
- The Linux package's `__main__.py` starts with a short shim. The image still passes `-w wine python.exe`, which 0.2.4 does not understand, so the shim re-executes the same host and port under Wine.
- The running terminal is `terminal64.exe`. The image's 32-bit `python.exe` cannot finish the IPC handshake with that build. The bridge must use 64-bit `C:\Python311\python.exe` with MetaTrader5 5.0.6231, numpy 1.26.4, and mt5linux 0.2.4. The watchdog passes that interpreter. The gateway reads `MT5_TERMINAL_PATH` and `MT5_PORTABLE=1` so the first login names the portable terminal. The connect page embeds that window at `/mt5-desktop/`. The UI process needs `MT5_DESKTOP_URL`, `MT5_DESKTOP_USER`, and `MT5_DESKTOP_PASSWORD` so the browser does not see the desktop login.

Those files live on the `mt5-config` volume, so a container restart keeps them. The image's `start.sh` is not rewritten: on boot it still runs the command above, finds `mt5linux` already installed, and the shim starts the 0.2.4 server. Published ports are left as the template set them. Port 8001 is only inside the container network.

`start.sh` starts the bridge once and exits. If that process dies later, the port stays closed. `scripts/mt5linux-bridge-watchdog.sh` checks every 60 seconds (systemd timer `mt5linux-bridge-watchdog.timer`) and, when 8001 is not listening and no bridge process is already starting, runs the same command again. The timer is on the host, so it still runs after the container restarts. It does not change the container's published ports.

If `scripts/test_mt5_connection.py` fails, check the bridge port first:

```bash
docker exec metatrader-5-ie74-mt5-1 ss -tulpn | grep 8001
```

No listener means the bridge is down. Then read `/config/mt5linux-bridge.log` inside the container and `systemctl status mt5linux-bridge-watchdog.timer` on the host. A missing login, password, or server is a later error: the script reaches the terminal and reports that credentials are not configured.
