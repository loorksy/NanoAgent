# Mokli deployment (Mokli v2 web client)

Mokli replaces the legacy React Mokli as the browser client. It is a thin client: every
turn, approval, background job and structured result is produced by the single mokli agent
behind the Agent API. Nothing in this stack runs a second model, a second memory or a second
pipeline.

```
Browser ──► caddy (:443, SITE_ADDRESS)
             ├── /api/v2/*, /ws/v2*, /v1/*  ──► mokli Agent API   host:8766
             └── everything else            ──► mokli-ui:8080

mokli-ui ──► host:8766/v1       OpenAI-compatible connection (models list, plain text chat)
mokli-ui ──► host:8766/api/v2   Pipe Function "Mokli" (SSE stream, approvals, results)
```

Files: `deploy/mokliui/docker-compose.yml`, `deploy/mokliui/Caddyfile`,
`deploy/mokliui/.env.example`, `deploy/mokliui/functions/mokli_pipe.py`.

## Prerequisites

- mokli running on the same host with the Agent API enabled (default `127.0.0.1:8766`).
  The Agent API starts with `mokli gateway`; see `agentApi` in the configuration section
  below.
- Docker Engine 24+ with the compose plugin. On Linux the containers reach mokli through
  `host.docker.internal`, which the compose file maps with `extra_hosts: host-gateway`.
- A DNS record for `SITE_ADDRESS` pointing at the host, with ports 80 and 443 reachable
  (Caddy obtains the Let's Encrypt certificate automatically).

## 1. Configure the Agent API on the mokli side

`~/.mokli/config.json`:

```json
{
  "agentApi": {
    "enabled": true,
    "host": "0.0.0.0",
    "port": 8766,
    "openaiCompat": true,
    "openaiModelName": "mokli",
    "corsOrigins": ["https://mokli.lork.cloud"]
  }
}
```

| Key | Default | Meaning |
| --- | --- | --- |
| `enabled` | `true` | Start the Agent API listener with the gateway. |
| `host` / `port` | `127.0.0.1` / `8766` | Bind address. The containers reach the host through the Docker bridge, so on Linux the default loopback bind is **not** reachable from Mokli: bind to `0.0.0.0` and block 8766 from the outside (`ufw deny 8766`, or an equivalent rule that keeps the docker bridge allowed), or bind to the bridge IP (`docker network inspect bridge -f '{{(index .IPAM.Config 0).Gateway}}'`, usually `172.17.0.1`). Caddy remains the only public entry point. |
| `bootstrapToken` | random | Static admin credential. When empty a random one is generated and written to `<workspace>/agent_api/admin_token`. |
| `tokenTtlSeconds` | `900` | Lifetime of short-lived web tokens. Device / pairing tokens never expire until revoked. |
| `openaiCompat` | `true` | Serve `/v1/models` and `/v1/chat/completions` on the same listener. Mokli needs this for its model connection. |
| `openaiModelName` | `mokli` | Model id returned by `/v1/models`. |
| `corsOrigins` | `[]` | Extra browser origins allowed to call the API directly (Mokli itself calls server-side; add the site origin only if you embed the API elsewhere). |
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
ADMIN=$(cat ~/.mokli/workspace/agent_api/admin_token)   # or agentApi.bootstrapToken

# 1) admin creates a one-time pairing code (valid 5 minutes)
curl -s -X POST http://127.0.0.1:8766/api/v2/devices/pairing-codes \
  -H "Authorization: Bearer $ADMIN" -H 'Content-Type: application/json' \
  -d '{"label":"mokli-ui"}'
# -> {"ok":true,"code":"48213377", ...}

# 2) redeem it (public endpoint) for the long-lived token
curl -s -X POST http://127.0.0.1:8766/api/v2/devices/pair \
  -H 'Content-Type: application/json' \
  -d '{"code":"48213377","label":"mokli-ui","locale":"ar"}'
# -> {"ok":true,"token":"nbat_...","expires_at":null,"client":{...}}
```

Put the `nbat_...` value in `.env` as `MOKLI_API_TOKEN`. To rotate it later:

```bash
curl -s -X POST http://127.0.0.1:8766/api/v2/devices/revoke-client \
  -H "Authorization: Bearer $ADMIN" -H 'Content-Type: application/json' \
  -d '{"client_id":"<client.id from step 2>"}'
```

## 3. Start the stack

```bash
cd deploy/mokliui
cp .env.example .env
openssl rand -hex 32          # -> MOKLI_SECRET_KEY
$EDITOR .env                  # SITE_ADDRESS, MOKLI_URL, ACME_EMAIL, MOKLI_SECRET_KEY, MOKLI_API_TOKEN
docker compose up -d
docker compose logs -f caddy mokli-ui
```

Open `https://<SITE_ADDRESS>/` and create the operator account: the first account becomes
admin. Then set `ENABLE_SIGNUP=false` in `.env` and run `docker compose up -d` again.
For a headless bootstrap set `MOKLI_ADMIN_EMAIL` / `MOKLI_ADMIN_PASSWORD` once instead; sign-up
is disabled automatically after the admin exists.

`ENABLE_PERSISTENT_CONFIG=false` makes the environment the single source of truth: every flag
in `docker-compose.yml` is re-applied on each start and cannot drift through the Admin UI.

## 4. Install the Mokli Pipe Function

The OpenAI connection alone gives plain streamed text. The Pipe Function adds the full Agent
API experience inside Mokli: Working / Waiting / Completed status lines, tool and
subagent timeline, structured results (`market`, `analysis`, `scenarios`, `risk`, `decision`,
`approval`, `plan_status`, `scorecard`) rendered as localized embeds, chart artifacts, HITL
confirmations, cancellation of a turn when the user stops generation, and notifications.

1. Admin Panel → **Functions** → **+** → paste the content of
   `deploy/mokliui/functions/mokli_pipe.py` → Save. Keep the function id `mokli`
   (derived from the frontmatter title) so the model id is `mokli.mokli`, which
   matches `MOKLI_DEFAULT_MODEL` in `.env`.
2. Open the function **Valves**:

   | Valve | Value |
   | --- | --- |
   | `GATEWAY_URL` | `http://host.docker.internal:8766` |
   | `GATEWAY_TOKEN` | the `nbat_...` token from step 2 |
   | `DEFAULT_LOCALE` | `ar` or `en` (used when Mokli does not send the user's locale) |
   | `SHOW_TIMELINE` | `true` to append the collapsible tool / subagent timeline to each reply |
   | `REQUEST_TIMEOUT` | REST/connect timeout in seconds; SSE reads never time out |

3. Enable the function (toggle) and, in Admin Panel → **Settings → Models**, hide the bare
   `mokli` model if you want a single entry in the picker.

Each Mokli chat maps to one mokli session (`X-Mokli-Session` header /
`X-Mokliui-Chat-Id`), so memory, sustained goals and approvals stay attached to the chat.

## 5. Legacy client

The React client and the public `/legacy/` route are removed. Mokli is the browser.
The gateway still serves the websocket channel's HTTP routes (settings, trading, channels,
media). TradingView's charting library stays at `mokli/public/charting_library/` and is
mounted by Mokli at `/charting_library/`. The gateway does not serve the old SPA.

## Operations

The Mokli image is built from the vendored tree in this repo (`mokli-mokli-ui:local`),
not pulled from a registry.

```bash
docker compose build mokli-ui && docker compose up -d   # build the local image and start
docker compose logs -f mokli-ui                # Pipe Function logs (logger mokli.pipe)
docker run --rm -v mokli-mokli_mokli-ui-data:/data -v "$PWD":/backup alpine \
  tar czf /backup/mokli-ui-data.tgz -C /data .  # back up chats / users / functions
```

### Troubleshooting

| Symptom | Check |
| --- | --- |
| Model list empty in Mokli | `docker compose exec mokli-ui curl -s -H "Authorization: Bearer $MOKLI_API_TOKEN" http://host.docker.internal:8766/v1/models`. On Linux confirm `host.docker.internal` resolves (needs `extra_hosts: host-gateway`) and that the Agent API is not bound to `127.0.0.1` only (see `agentApi.host` above). |
| `401 auth.invalid_token` in pipe logs | Token revoked or mistyped; issue a new one (step 2) and update both `.env` and the valve. |
| Replies stall after a few minutes behind Caddy | Ensure the `Caddyfile` in use still has `flush_interval -1` and zero `read_timeout` / `write_timeout` for the Agent API and Mokli upstreams. |
| Structured results show as raw JSON | The Pipe Function is disabled or the chat uses the bare `mokli` model; select `Mokli` (pipe) in the model picker. |
| Certificate not issued | Ports 80/443 must be reachable from the internet and `SITE_ADDRESS` must resolve to this host; see `docker compose logs caddy`. |

## Testing

```bash
uv run --no-sync pytest tests/deploy tests/agent_api -q
```

`tests/deploy/test_mokli_pipe.py` exercises the Pipe Function against a fake Agent API
(SSE parsing, resume via `Last-Event-ID`, approval confirmation, cancellation, embeds and
localized labels). `tests/agent_api` covers the routes the pipe relies on.
