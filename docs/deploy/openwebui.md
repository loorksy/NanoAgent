# Open WebUI deployment (NanoAgent v2 web client)

Open WebUI replaces the legacy React WebUI as the browser client. It is a thin client: every
turn, approval, background job and structured result is produced by the single nanobot agent
behind the Agent API. Nothing in this stack runs a second model, a second memory or a second
pipeline.

```
Browser ──► caddy (:443, SITE_ADDRESS)
             ├── /api/v2/*, /ws/v2*, /v1/*  ──► nanobot Agent API   host:8766
             └── everything else            ──► open-webui:8080

open-webui ──► host:8766/v1       OpenAI-compatible connection (models list, plain text chat)
open-webui ──► host:8766/api/v2   Pipe Function "NanoAgent" (SSE stream, approvals, results)
```

Files: `deploy/openwebui/docker-compose.yml`, `deploy/openwebui/Caddyfile`,
`deploy/openwebui/.env.example`, `deploy/openwebui/functions/nanoagent_pipe.py`.

## Prerequisites

- nanobot running on the same host with the Agent API enabled (default `127.0.0.1:8766`).
  The Agent API starts with `nanobot gateway`; see `agentApi` in the configuration section
  below.
- Docker Engine 24+ with the compose plugin. On Linux the containers reach nanobot through
  `host.docker.internal`, which the compose file maps with `extra_hosts: host-gateway`.
- A DNS record for `SITE_ADDRESS` pointing at the host, with ports 80 and 443 reachable
  (Caddy obtains the Let's Encrypt certificate automatically).

## 1. Configure the Agent API on the nanobot side

`~/.nanobot/config.json`:

```json
{
  "agentApi": {
    "enabled": true,
    "host": "0.0.0.0",
    "port": 8766,
    "openaiCompat": true,
    "openaiModelName": "nanoagent",
    "corsOrigins": ["https://nanoagent.lork.cloud"]
  }
}
```

| Key | Default | Meaning |
| --- | --- | --- |
| `enabled` | `true` | Start the Agent API listener with the gateway. |
| `host` / `port` | `127.0.0.1` / `8766` | Bind address. The containers reach the host through the Docker bridge, so on Linux the default loopback bind is **not** reachable from Open WebUI: bind to `0.0.0.0` and block 8766 from the outside (`ufw deny 8766`, or an equivalent rule that keeps the docker bridge allowed), or bind to the bridge IP (`docker network inspect bridge -f '{{(index .IPAM.Config 0).Gateway}}'`, usually `172.17.0.1`). Caddy remains the only public entry point. |
| `bootstrapToken` | random | Static admin credential. When empty a random one is generated and written to `<workspace>/agent_api/admin_token`. |
| `tokenTtlSeconds` | `900` | Lifetime of short-lived web tokens. Device / pairing tokens never expire until revoked. |
| `openaiCompat` | `true` | Serve `/v1/models` and `/v1/chat/completions` on the same listener. Open WebUI needs this for its model connection. |
| `openaiModelName` | `nanoagent` | Model id returned by `/v1/models`. |
| `corsOrigins` | `[]` | Extra browser origins allowed to call the API directly (Open WebUI itself calls server-side; add the site origin only if you embed the API elsewhere). |
| `eventRetentionDays` | `7` | How long timeline events are kept for SSE resume / `GET /sessions/{id}/timeline`. |

Restart the gateway and check:

```bash
curl -s http://127.0.0.1:8766/api/v2/health
```

## 2. Obtain the gateway token

The Pipe Function and the OpenAI connection authenticate with a bearer token. Use a
non-expiring **device** token issued through the pairing flow instead of the admin token, so the
web client only holds the `chat / read / approve / control / push` scopes:

```bash
ADMIN=$(cat ~/.nanobot/workspace/agent_api/admin_token)   # or agentApi.bootstrapToken

# 1) admin creates a one-time pairing code (valid 5 minutes)
curl -s -X POST http://127.0.0.1:8766/api/v2/devices/pairing-codes \
  -H "Authorization: Bearer $ADMIN" -H 'Content-Type: application/json' \
  -d '{"label":"open-webui"}'
# -> {"ok":true,"code":"48213377", ...}

# 2) redeem it (public endpoint) for the long-lived token
curl -s -X POST http://127.0.0.1:8766/api/v2/devices/pair \
  -H 'Content-Type: application/json' \
  -d '{"code":"48213377","label":"open-webui","locale":"ar"}'
# -> {"ok":true,"token":"nbat_...","expires_at":null,"client":{...}}
```

Put the `nbat_...` value in `.env` as `NANOAGENT_API_TOKEN`. To rotate it later:

```bash
curl -s -X POST http://127.0.0.1:8766/api/v2/devices/revoke-client \
  -H "Authorization: Bearer $ADMIN" -H 'Content-Type: application/json' \
  -d '{"client_id":"<client.id from step 2>"}'
```

## 3. Start the stack

```bash
cd deploy/openwebui
cp .env.example .env
openssl rand -hex 32          # -> WEBUI_SECRET_KEY
$EDITOR .env                  # SITE_ADDRESS, WEBUI_URL, ACME_EMAIL, WEBUI_SECRET_KEY, NANOAGENT_API_TOKEN
docker compose up -d
docker compose logs -f caddy open-webui
```

Open `https://<SITE_ADDRESS>/` and create the operator account: the first account becomes
admin. Then set `ENABLE_SIGNUP=false` in `.env` and run `docker compose up -d` again.
For a headless bootstrap set `WEBUI_ADMIN_EMAIL` / `WEBUI_ADMIN_PASSWORD` once instead; sign-up
is disabled automatically after the admin exists.

`ENABLE_PERSISTENT_CONFIG=false` makes the environment the single source of truth: every flag
in `docker-compose.yml` is re-applied on each start and cannot drift through the Admin UI.

## 4. Install the NanoAgent Pipe Function

The OpenAI connection alone gives plain streamed text. The Pipe Function adds the full Agent
API experience inside Open WebUI: Working / Waiting / Completed status lines, tool and
subagent timeline, structured results (`market`, `analysis`, `scenarios`, `risk`, `decision`,
`approval`, `plan_status`, `scorecard`) rendered as localized embeds, chart artifacts, HITL
confirmations, cancellation of a turn when the user stops generation, and notifications.

1. Admin Panel → **Functions** → **+** → paste the content of
   `deploy/openwebui/functions/nanoagent_pipe.py` → Save. Keep the function id `nanoagent`
   (derived from the frontmatter title) so the model id is `nanoagent.nanoagent`, which
   matches `NANOAGENT_DEFAULT_MODEL` in `.env`.
2. Open the function **Valves**:

   | Valve | Value |
   | --- | --- |
   | `GATEWAY_URL` | `http://host.docker.internal:8766` |
   | `GATEWAY_TOKEN` | the `nbat_...` token from step 2 |
   | `DEFAULT_LOCALE` | `ar` or `en` (used when Open WebUI does not send the user's locale) |
   | `SHOW_TIMELINE` | `true` to append the collapsible tool / subagent timeline to each reply |
   | `REQUEST_TIMEOUT` | REST/connect timeout in seconds; SSE reads never time out |

3. Enable the function (toggle) and, in Admin Panel → **Settings → Models**, hide the bare
   `nanoagent` model if you want a single entry in the picker.

Each Open WebUI chat maps to one nanobot session (`X-NanoAgent-Session` header /
`X-OpenWebUI-Chat-Id`), so memory, sustained goals and approvals stay attached to the chat.

## 5. Legacy client

The React client and the public `/legacy/` route are removed. Open WebUI is the browser.
The gateway still serves the websocket channel's HTTP routes (settings, trading, channels,
media). TradingView's charting library stays at `webui/public/charting_library/` and is
mounted by Open WebUI at `/charting_library/`. The gateway does not serve the old SPA.

## Operations

The Open WebUI image is built from the vendored tree in this repo (`nanoagent-open-webui:local`),
not pulled from a registry.

```bash
docker compose build open-webui && docker compose up -d   # build the local image and start
docker compose logs -f open-webui                # Pipe Function logs (logger nanoagent.pipe)
docker run --rm -v nanoagent-webui_open-webui-data:/data -v "$PWD":/backup alpine \
  tar czf /backup/open-webui-data.tgz -C /data .  # back up chats / users / functions
```

### Troubleshooting

| Symptom | Check |
| --- | --- |
| Model list empty in Open WebUI | `docker compose exec open-webui curl -s -H "Authorization: Bearer $NANOAGENT_API_TOKEN" http://host.docker.internal:8766/v1/models`. On Linux confirm `host.docker.internal` resolves (needs `extra_hosts: host-gateway`) and that the Agent API is not bound to `127.0.0.1` only (see `agentApi.host` above). |
| `401 auth.invalid_token` in pipe logs | Token revoked or mistyped; issue a new one (step 2) and update both `.env` and the valve. |
| Replies stall after a few minutes behind Caddy | Ensure the `Caddyfile` in use still has `flush_interval -1` and zero `read_timeout` / `write_timeout` for the Agent API and Open WebUI upstreams. |
| Structured results show as raw JSON | The Pipe Function is disabled or the chat uses the bare `nanoagent` model; select `NanoAgent` (pipe) in the model picker. |
| Certificate not issued | Ports 80/443 must be reachable from the internet and `SITE_ADDRESS` must resolve to this host; see `docker compose logs caddy`. |

## Testing

```bash
uv run --no-sync pytest tests/deploy tests/agent_api -q
```

`tests/deploy/test_nanoagent_pipe.py` exercises the Pipe Function against a fake Agent API
(SSE parsing, resume via `Last-Event-ID`, approval confirmation, cancellation, embeds and
localized labels). `tests/agent_api` covers the routes the pipe relies on.
