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
| `MT5_LOGIN` | no | | Account number. Leave empty when the Connect page saves the account. |
| `MT5_PASSWORD` | no | | Trading password. Leave empty for the Connect page. Never commit it. |
| `MT5_SERVER` | no | | Broker server name. Leave empty for the Connect page. |
| `MT5_TERMINAL_PATH` | no | generic `terminal64.exe` | Portable terminal the bridge attaches to. In `.env`, double every backslash. |
| `MT5_PORTABLE` | no | `1` | Pass `portable=True` into `initialize()`. |
| `MT5_IPC_TIMEOUT_MS` | no | `45000` | How long the first login waits for the terminal. |
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
- The running terminal is `terminal64.exe`. The image's 32-bit `python.exe` cannot finish the IPC handshake with that build. The bridge must use 64-bit `C:\Python311\python.exe` with MetaTrader5 5.0.6231, numpy 1.26.4, and mt5linux 0.2.4. The watchdog passes that interpreter. The gateway reads `MT5_TERMINAL_PATH` and `MT5_PORTABLE=1` so the first login names the portable terminal. The connect page searches for the broker company, then collects the account number, trading password, and one of that company's servers. The gateway dials the server's access address. The UI process can still proxy the desktop at `/mt5-desktop/` with `MT5_DESKTOP_URL`, `MT5_DESKTOP_USER`, and `MT5_DESKTOP_PASSWORD` so the browser does not see the desktop login.

Those files live on the `mt5-config` volume, so a container restart keeps them. The image's `start.sh` is not rewritten: on boot it still runs the command above, finds `mt5linux` already installed, and the shim starts the 0.2.4 server. Published ports are left as the template set them. Port 8001 is only inside the container network.

`start.sh` starts the bridge once and exits. If that process dies later, the port stays closed. `scripts/mt5linux-bridge-watchdog.sh` checks every 60 seconds (systemd timer `mt5linux-bridge-watchdog.timer`) and, when 8001 is not listening and no bridge process is already starting, runs the same command again. The timer is on the host, so it still runs after the container restarts. It does not change the container's published ports.

If `scripts/test_mt5_connection.py` fails, check the bridge port first:

```bash
docker exec metatrader-5-ie74-mt5-1 ss -tulpn | grep 8001
```

No listener means the bridge is down. Then read `/config/mt5linux-bridge.log` inside the container and `systemctl status mt5linux-bridge-watchdog.timer` on the host. A missing login, password, or server is a later error: the script reaches the terminal and reports that credentials are not configured.

## Same layout on another host

The running host keeps code in `/opt/nanoagent` on `main`. These files are not in git because they hold secrets or live data, and a new host creates them locally:

- `/opt/nanoagent/.env` from `.env.example`
- `/opt/nanoagent/mokli-ui.env` from `deploy/nanoagent/mokli-ui.env.example`
- `/opt/nanoagent/.mokli/` (config and the encrypted secret store)
- `/opt/nanoagent/mokli-ui/data/` (the UI database)
- `/opt/nanoagent/mokli-ui/build/` (produced by `npm run build`)

`scripts/deploy-mokli-vps.sh` installs a different tree at `/opt/mokli`. Do not run it on a host that already serves this domain.

The UI unit sets `PYTHONPATH=/opt/nanoagent` so the UI process can import Mokli. The public name is routed by `deploy/traefik/nanoagent.yml` to `127.0.0.1:8080`.

`scripts/install-mt5linux-bridge.sh` is what a new container needs. When `C:\Python311\python.exe` already imports MetaTrader5 5.0.6231, numpy 1.26.4, mt5linux 0.2.4, and rpyc 5.2.3, it leaves the container alone. Otherwise it installs 64-bit Python 3.11.9 from python.org and those pins, then the Linux mt5linux 0.2.4 client. `scripts/install-mt5linux-shim.sh` copies the Wine bridge entrypoint when it is missing. Neither script restarts the container or changes its published ports. The watchdog then starts `C:\Python311\python.exe`. The image's 32-bit `python.exe` and mt5linux 1.1.1 do not complete the handshake.

## What the programmer runs

From a checkout of `main`, as root:

```bash
sudo NANOAGENT_BOOTSTRAP=1 scripts/install-nanoagent-host.sh
```

That command installs git, Python 3.11, Node.js 22 when they are missing, both virtualenvs, the UI build, the systemd units, the bridge watchdog, and the bridge pins inside a running MT5 container. It copies `deploy/traefik/nanoagent.yml` only when `/docker/traefik/dynamic/` exists and `nanoagent.yml` is not already there. Edit the `Host` rule for another domain, then reload Traefik.

The script creates the two env files from the examples and does not fill secrets. It does set `MT5_HOST` when that line is still `localhost` or empty, using the running container's address, and it does not print the address. A value you already chose is left as it is.

Fill only the blank keys the script prints:

| File | Key | What to put |
| --- | --- | --- |
| `/opt/nanoagent/.env` | `OANDA_API_TOKEN`, `OANDA_ACCOUNT_ID` | Market-data credentials. Leave them blank if this host does not use OANDA. |
| `/opt/nanoagent/.env` | `MT5_LOGIN`, `MT5_PASSWORD`, `MT5_SERVER` | Leave empty. The Connect page stores the account after a live login. |
| `/opt/nanoagent/mokli-ui.env` | `MOKLI_SECRET_KEY` | A new random value: `openssl rand -hex 32`. Do not rotate it later; sessions are signed with it. |
| `/opt/nanoagent/mokli-ui.env` | `MOKLI_API_TOKEN` | After the gateway has started once, copy the file `/opt/nanoagent/.mokli/workspace/agent_api/admin_token`. Do not print it. |
| `/opt/nanoagent/mokli-ui.env` | `MT5_DESKTOP_USER`, `MT5_DESKTOP_PASSWORD` | The desktop login for the MT5 container, only if you use `/mt5-desktop/`. |

Then start the services:

```bash
sudo NANOAGENT_RESTART=1 scripts/install-nanoagent-host.sh
```

The second run does not reinstall packages. It reloads the units, restarts the gateway and the UI, and skips the Wine installer when the pins already match.
