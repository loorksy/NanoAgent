# Deployment

Use this page after `mokli agent -m "Hello!"` works locally. Deployment keeps long-running surfaces online: Mokli, chat apps, heartbeat, Dream, cron jobs, and channel connections.

## Before You Deploy

Check these once before Render, Docker, systemd, or LaunchAgent:

| Check | Why it matters |
|---|---|
| `mokli status` shows the expected config and workspace | Confirms the process will read the instance you meant to run |
| `mokli agent -m "Hello!"` works | Proves install, config, provider, model, and workspace writes before adding a service layer |
| Secrets are in environment variables or protected config files | API keys, bot tokens, OAuth state, and chat credentials should not be world-readable |
| The active config directory (including `sessions/`) and workspace are persistent | Sessions follow `--config`; memory, generated artifacts, and the workspace identity marker follow the workspace |
| Channel access control is intentional | Use `allowFrom`, pairing, WebSocket `token`/`tokenIssueSecret`, or private test channels before exposing the bot |
| Ports are planned | Gateway health defaults to local-only `127.0.0.1:18790`; Mokli/WebSocket defaults to `8765`; `mokli serve` defaults to `8900` |
| Logs are easy to reach | Use `docker compose logs`, `journalctl`, LaunchAgent log files, or `mokli gateway --verbose` while diagnosing startup |

Restart the deployed process after editing `config.json`. Long-running processes read config at startup.

## Choose a Runtime

| Runtime | Use it for | State location | Useful first command |
|---|---|---|---|
| Render | One-click hosted gateway and Mokli | Persistent disk at `/home/mokli/.mokli` | [Deploy to Render](#render) |
| Docker Compose | Repeatable container runs on Linux servers or workstations | Bind-mount `~/.mokli` to `/home/mokli/.mokli` | `docker compose run --rm mokli-cli agent -m "Hello!"` |
| Docker CLI | Manual container testing or small one-off hosts | Bind-mount `~/.mokli` to `/home/mokli/.mokli` | `docker run -v ~/.mokli:/home/mokli/.mokli --rm mokli status` |
| systemd user service | Linux user-level gateway that restarts automatically | Host user's `~/.mokli` unless you pass explicit paths | `systemctl --user status mokli-gateway` |
| macOS LaunchAgent | macOS gateway that starts after login | Host user's `~/.mokli` unless the plist passes explicit paths | `launchctl list | grep ai.mokli.gateway` |

## Render

Run mokli online without managing a server. The blueprint deploys the gateway and bundled Mokli together, with a persistent disk so sessions, memory, and chat history survive restarts.

> [!IMPORTANT]
> This setup requires a paid Render service because persistent disks are not available on the free tier. During setup, provide `ANTHROPIC_API_KEY` and set `MOKLI_WEB_TOKEN` to a strong private password (for example, generate one with `openssl rand -hex 32`).

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/HKUDS/nanobot)

[Review the deployment blueprint](../render.yaml)

### First Deployment

1. Click **Deploy to Render**, sign in, and review the Blueprint. It creates one Starter web service and a 1 GB persistent disk.
2. Enter your `ANTHROPIC_API_KEY`. Set `MOKLI_WEB_TOKEN` to a new random value and save it in your password manager; this is the password for the public Mokli.
3. Create the Blueprint and wait for the service status to become **Live**. The first build can take several minutes.
4. Open the generated `onrender.com` URL. The **Authentication required** page means the gateway is running: enter the same `MOKLI_WEB_TOKEN` value to open the Mokli.

The model API key is used by mokli to call Anthropic. The Web token only protects access to this deployment; do not share it in issues, screenshots, or chat.

### Updates and Data

The Blueprint disables automatic deploys so upstream repository changes do not unexpectedly restart your agent. To update, open the service in the Render Dashboard and choose **Manual Deploy → Deploy latest commit**.

The persistent disk keeps `config.json`, sessions, memory, Mokli history, cron state, media, and logs across restarts and updates. The deployment initializes `config.json` only when it does not already exist, so settings changed later in the Mokli are not replaced on every boot.

If deployment fails, open the service **Logs** page first. A missing model key fails provider requests after startup, while an incorrect Web token leaves you on the authentication page.

## Docker

> [!TIP]
> The `-v ~/.mokli:/home/mokli/.mokli` flag mounts your local config directory into the container, so your config and workspace persist across container restarts.
> The container runs as the non-root user `mokli` (UID 1000) and reads config from `/home/mokli/.mokli`. Always mount your host config directory to `/home/mokli/.mokli`, not `/root/.mokli`.
> If you get **Permission denied**, fix ownership on the host first: `sudo chown -R 1000:1000 ~/.mokli`, or pass `--user $(id -u):$(id -g)` to match your host UID. Podman users can use `--userns=keep-id` instead.
>
> [!IMPORTANT]
> Official Docker usage currently means building from this repository with the included `Dockerfile`. Docker Hub images under third-party namespaces are not maintained or verified by HKUDS/nanobot; do not mount API keys or bot tokens into them unless you trust the publisher.

> [!IMPORTANT]
> The gateway and WebSocket channel default to `host: "127.0.0.1"` in `config.json` (set in `mokli/config/schema.py`). Docker `-p` port forwarding cannot reach a container's loopback interface, so for the host or LAN to reach the exposed ports you must set both binds to `0.0.0.0` in `~/.mokli/config.json` before starting the container. To serve the bundled Mokli from Docker, bind the WebSocket channel externally and protect bootstrap with `tokenIssueSecret`:
>
> ```json
> {
>   "gateway": { "host": "0.0.0.0" },
>   "channels": {
>     "websocket": {
>       "host": "0.0.0.0",
>       "port": 8765,
>       "tokenIssueSecret": "your-secret-here"
>     }
>   }
> }
> ```
>
> When the WebSocket `host` is `0.0.0.0`, the channel refuses to start unless `token`, `tokenIssueSecret`, or a fully configured `trustedProxyAuth` is also configured. See [`mokli.md#lan-access`](./mokli.md#lan-access) for details.
> The gateway health route itself is intentionally minimal and unauthenticated. When the
> container binds it to `0.0.0.0`, publish port `18790` to host loopback only; place any
> remotely monitored health endpoint behind a firewall or reverse proxy. If another host
> must probe it directly, replace `127.0.0.1` in the port mapping with a trusted host
> interface and restrict inbound traffic to the monitoring system.

### Cloudflare Tunnel + Cloudflare Access

For a local `cloudflared` process in front of mokli, Cloudflare Access can
authenticate the user before forwarding the request and add
`Cf-Access-Jwt-Assertion`. Opt in to trusted-proxy no-token mode only when the
direct TCP peer is the tunnel process and the assertion is non-empty:

```json
{
  "gateway": { "host": "127.0.0.1" },
  "channels": {
    "websocket": {
      "host": "127.0.0.1",
      "port": 8765,
      "publicWsUrl": "wss://mokli.example.com/",
      "trustedProxyAuth": {
        "trustedPeerCidrs": ["127.0.0.1/32", "::1/128"],
        "assertionHeader": "Cf-Access-Jwt-Assertion"
      }
    }
  }
}
```

This is two-part authorization: a trusted direct loopback peer **and** a
non-empty Cloudflare Access assertion. A trusted CIDR alone is not a bypass.
For this flow `/mokli/bootstrap` returns connection metadata without a
bootstrap token or REST API token; the proxy assertion authorizes the WebSocket
handshake and REST requests directly.

Set `publicWsUrl` to the browser-facing `wss://` endpoint when the tunnel sends
the origin host header (such as `127.0.0.1:8765`); otherwise the Mokli could
attempt to open its WebSocket directly against the loopback address.
The assertion header must be generated
by Cloudflare Access after authentication; routing/client metadata headers such
as `Host`, `Forwarded`, `X-Forwarded-*`, `X-Real-IP`, and `CF-Connecting-IP`
are rejected as `assertionHeader` values. Mokli trusts the assertion but does
not cryptographically validate the JWT, so configure the tunnel and Access
policy carefully and do not expose the mokli listener directly to untrusted
clients. Forwarded client headers do not establish proxy trust.

### Docker Compose

The default image preinstalls WhatsApp dependencies. To bake other enabled
channels into an image (recommended for deployments without PyPI access), pass
a comma-separated `MOKLI_CHANNELS` build argument:

```bash
MOKLI_CHANNELS=telegram,slack docker compose build
```

The image keeps mokli in a virtual environment owned by its built-in non-root
runtime user (UID 1000). If an enabled channel was not preinstalled, gateway
startup can therefore install its manifest-declared dependencies. Rebuilding
with `MOKLI_CHANNELS` keeps that installation reproducible instead of relying
on the container's writable layer. If you override the container with a
different `--user`, bake every enabled channel into the image because that UID
is not guaranteed write access to the virtual environment.

```bash
docker compose run --rm mokli-cli onboard   # first-time setup
vim ~/.mokli/config.json                     # add API keys
docker compose up -d mokli-gateway           # start gateway
```

```bash
docker compose run --rm mokli-cli agent -m "Hello!"   # run CLI
docker compose logs -f mokli-gateway                   # view logs
docker compose down                                      # stop
```

The default Compose file drops all Linux capabilities except `CHOWN`, `SETUID`, and
`SETGID`, which the root entrypoint needs to fix bind-mount ownership and become UID
1000. It also enables `no-new-privileges`, so the non-root process cannot regain those
bootstrap capabilities through setuid binaries or file capabilities. Docker's default
AppArmor/seccomp profiles remain enabled. If you explicitly set
`"tools.exec.sandbox": "bwrap"` in `~/.mokli/config.json`, add the bwrap
override file when starting containers:

```bash
docker compose -f docker-compose.yml -f docker-compose.bwrap.yml up -d mokli-gateway
docker compose -f docker-compose.yml -f docker-compose.bwrap.yml run --rm mokli-cli agent -m "Hello!"
```

The override adds `CAP_SYS_ADMIN` and disables AppArmor/seccomp confinement for the
container so bubblewrap can create its nested namespaces. It preserves
`no-new-privileges`. The host must also allow unprivileged user namespaces; the
override cannot bypass a host-level namespace restriction. Use it only when the
bwrap sandbox is enabled.

### Docker

```bash
# Build the image
docker build -t mokli .

# Or preinstall a regular Python extra such as Bedrock support
docker build --build-arg MOKLI_EXTRAS=bedrock -t mokli .

# Or preinstall dependencies for a specific set of channels
docker build --build-arg MOKLI_CHANNELS=telegram,slack -t mokli .

# Initialize config (first time only)
docker run -v ~/.mokli:/home/mokli/.mokli --rm mokli onboard

# Edit config on host to add API keys
vim ~/.mokli/config.json

# Run gateway (connects to enabled channels, e.g. Telegram/Discord/Mochat).
# `-p 8765:8765` exposes the WebSocket channel / Mokli alongside the gateway
# health endpoint on 18790.
docker run \
  --cap-drop ALL \
  --cap-add CHOWN --cap-add SETGID --cap-add SETUID \
  --security-opt no-new-privileges:true \
  -v ~/.mokli:/home/mokli/.mokli \
  -p 18790:18790 -p 8765:8765 \
  mokli gateway

# If `tools.exec.sandbox: "bwrap"` is enabled, run with the extra permissions
# bubblewrap needs for nested namespaces. Without them, `bwrap` may exit with
# `clone3: Operation not permitted`.
docker run \
  --cap-drop ALL \
  --cap-add CHOWN --cap-add SETGID --cap-add SETUID --cap-add SYS_ADMIN \
  --security-opt no-new-privileges:true \
  --security-opt apparmor=unconfined \
  --security-opt seccomp=unconfined \
  -v ~/.mokli:/home/mokli/.mokli \
  -p 127.0.0.1:18790:18790 -p 8765:8765 \
  mokli gateway

# Or run a single command
docker run -v ~/.mokli:/home/mokli/.mokli --rm mokli agent -m "Hello!"
docker run -v ~/.mokli:/home/mokli/.mokli --rm mokli status
```

## Linux Service

Run the gateway as a systemd user service so it starts automatically and restarts on failure.

Preview the generated unit first:

```bash
mokli gateway install-service --manager systemd --dry-run
```

Install, enable, and start it:

```bash
mokli gateway install-service --manager systemd
```

For a custom instance, pass the same config/workspace selector you use to run the gateway:

```bash
mokli gateway install-service \
  --manager systemd \
  --name mokli-telegram \
  --config ~/.mokli-telegram/config.json \
  --workspace ~/.mokli-telegram/workspace
```

Common operations:

```bash
systemctl --user status mokli-gateway        # check status
systemctl --user restart mokli-gateway       # restart after config changes
journalctl --user -u mokli-gateway -f        # follow logs
mokli gateway uninstall-service --manager systemd
```

The installer writes `~/.config/systemd/user/mokli-gateway.service`, runs
`systemctl --user daemon-reload`, enables the unit, and restarts it. It uses the
current Python executable with `python -m mokli gateway --foreground`, so the
service runs in the same environment you used to install mokli.

> **Note:** User services only run while you are logged in. To keep the gateway running after logout, enable lingering:
>
> ```bash
> loginctl enable-linger $USER
> ```

## macOS LaunchAgent

Use a LaunchAgent when you want `mokli gateway` to stay online after you log in, without keeping a terminal open.

Preview the generated plist first:

```bash
mokli gateway install-service --manager launchd --dry-run
```

Install, load, enable, and start it:

```bash
mokli gateway install-service --manager launchd
```

For a custom instance:

```bash
mokli gateway install-service \
  --manager launchd \
  --name mokli-telegram \
  --config ~/.mokli-telegram/config.json \
  --workspace ~/.mokli-telegram/workspace
```

Common operations:

```bash
launchctl list | grep ai.mokli.gateway
launchctl kickstart -k gui/$(id -u)/ai.mokli.gateway
mokli gateway uninstall-service --manager launchd
```

The installer writes `~/Library/LaunchAgents/ai.mokli.gateway.plist`, uses the
current Python executable with `python -m mokli gateway --foreground`, and
writes LaunchAgent logs under `~/.mokli/logs/`.

> **Note:** if startup fails with "address already in use", stop the manually started `mokli gateway` process first.
