# Mokli fork of Mokli

Upstream: [mokli-ui/mokli-ui](https://github.com/open-webui/open-webui) tag `v0.11.4`
(`8bd8b4fac5e059578ac0c74b3c18d11139f88b7d`).

This tree is the web client. The agent, tools, gates, and memory stay in `mokli/`.
The browser never receives the long-lived gateway token. Svelte pages call
`/api/v1/mokli/*`, and `backend/mokli_ui/routers/mokli.py` forwards
that to `MOKLI_GATEWAY_URL` (`/api/v2/...`) with `MOKLI_API_TOKEN`.

## Added

- Sidebar sections: Agent (`/`), Tasks (`/tasks`), Recommendations (`/recommendations`), Connect (`/connect`), Log (`/log`).
- Tasks calls `/api/v2/tasks`, an alias of `/api/v2/jobs` (list, pause, resume, cancel), plus pending approvals, `GET /api/v2/tasks/desk`, and `POST /api/v2/tasks/lab` (strategy replay; not an order).
- The collapsed sidebar shows an icon for each Mokli section. The expanded sidebar shows the icon and the section name.
- Log adds journal and calendar sections (`/api/v2/log/journal`, `/api/v2/log/calendar`).
- Settings → Models reads `GET /api/v2/settings/models` (provider names only, no API keys).
- Settings → Capabilities and System read `GET /api/v2/settings/capabilities` and `GET /api/v2/settings/system`. Those documents list flags, timezone, and the listener address. They do not include the bootstrap token.
- Connect shows feed and broker cards, a two-step kill switch, pause/resume, and the seven risk sliders. Labels on those sliders come from the gateway payload.
- Settings tabs: Overview, Models, Channels, Capabilities, System, Advanced, Risk. Appearance is the Mokli Interface tab. About keeps the upstream page plus the branding limit below.
- Pipe Function source: `functions/mokli_pipe.py` (install from Admin → Functions, or rely on the copy in `deploy/mokliui/functions/`).
- Agent status strip above the main slot.

## Hidden in this fork

Notes, Workspace, Playground, Automations, Calendar, and Mokli Channels.
Personalization, Audio, direct Connections, and Tools settings tabs.

## Branding

Mokli's license allows a custom name for deployments of at most 50 users
in 30 days. `MOKLI_NAME` defaults to Mokli. Above that limit, keep the
Mokli name in About or obtain an enterprise license.
