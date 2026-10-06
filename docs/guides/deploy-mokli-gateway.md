# How to Deploy a Long-Running mokli AI Agent Gateway

The mokli gateway is the long-running self-hosted AI agent process that keeps
Mokli sessions, chat apps, automations, local triggers, heartbeat jobs, Dream,
and WebSocket delivery online.

## What you will build

- a verified mokli config
- a gateway process
- a service or container deployment path with Docker, systemd, or macOS
  LaunchAgent

## When to use this

Use this when mokli should keep running after a single CLI turn. Chat apps,
browser sessions, background automations, local triggers, and server-side
integrations all depend on a live gateway.

## Install

```bash
python -m pip install mokli-ai
mokli onboard --wizard
mokli status
mokli agent -m "Hello!"
```

## Minimal working example

Run the gateway in the foreground:

```bash
mokli gateway
```

For Mokli background usage:

```bash
mokli gateway --background
mokli gateway status
mokli gateway logs
```

Open the configured Mokli URL in a browser, or run `mokli mokli` as a foreground client.

## Production notes

- Docker Compose is the most repeatable Linux container path.
- systemd user services are useful for Linux user-level gateway deployments.
- macOS LaunchAgent keeps the gateway alive after login.
- Persist the active config directory's `sessions/` folder together with the workspace
  (including `.mokli/workspace-id`), memory files, channel login state, and generated artifacts.
- Restart the gateway after editing `config.json`.

## Security notes

- Plan ports before exposing services. Gateway health defaults to `18790`,
  Mokli/WebSocket defaults to `8765`, and `mokli serve` defaults to `8900`.
- Bind externally only when you have configured tokens or API keys.
- Keep chat access control intentional before deploying.
- Use Docker or Linux sandboxing when shell tools are enabled for unattended
  work.

## Troubleshooting

- Use the same `--config` and `--workspace` flags for status checks and service
  startup.
- Check logs with `docker compose logs`, `journalctl`, LaunchAgent logs, or
  `mokli gateway --verbose`.
- If Docker port publishing does not work, confirm the service is not bound only
  to container loopback.

## Related mokli docs

- [Deployment](../deployment.md)
- [Multiple Instances](../multiple-instances.md)
- [Configuration](../configuration.md)
