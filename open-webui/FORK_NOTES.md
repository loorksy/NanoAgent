# NanoAgent fork of Open WebUI

Upstream: [open-webui/open-webui](https://github.com/open-webui/open-webui) tag `v0.11.4`
(`8bd8b4fac5e059578ac0c74b3c18d11139f88b7d`).

This tree is the web client. The agent, tools, gates, and memory stay in `nanobot/`.
The browser never receives the long-lived gateway token. Svelte pages call
`/api/v1/nanoagent/*`, and `backend/open_webui/routers/nanoagent.py` forwards
that to `NANOAGENT_GATEWAY_URL` (`/api/v2/...`) with `NANOAGENT_API_TOKEN`.

## Added

- Sidebar sections: Agent (`/`), Tasks (`/tasks`), Recommendations (`/recommendations`), Connect (`/connect`), Log (`/log`).
- Tasks calls `/api/v2/tasks`, an alias of `/api/v2/jobs` (list, pause, resume, cancel), plus pending approvals and `GET /api/v2/tasks/desk`.
- Log adds journal and calendar sections (`/api/v2/log/journal`, `/api/v2/log/calendar`).
- Settings → Models reads `GET /api/v2/settings/models` (provider names only, no API keys).
- Connect shows feed and broker cards, a two-step kill switch, pause/resume, and the seven risk sliders. Labels on those sliders come from the gateway payload.
- Settings tabs: Overview, Models, Channels, Capabilities, System, Advanced, Risk. Appearance is the Open WebUI Interface tab. About keeps the upstream page plus the branding limit below.
- Pipe Function source: `functions/nanoagent_pipe.py` (install from Admin → Functions, or rely on the copy in `deploy/openwebui/functions/`).
- Agent status strip above the main slot.

## Hidden in this fork

Notes, Workspace, Playground, Automations, Calendar, and Open WebUI Channels.
Personalization, Audio, direct Connections, and Tools settings tabs.

## Branding

Open WebUI's license allows a custom name for deployments of at most 50 users
in 30 days. `WEBUI_NAME` defaults to NanoAgent. Above that limit, keep the
Open WebUI name in About or obtain an enterprise license.
