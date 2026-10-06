# Mokli web client

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
- Settings tabs: Overview, Models, Channels, Capabilities, System, Advanced, Risk. Appearance is the Mokli Interface tab.
- Pipe Function source: `functions/mokli_pipe.py` (install from Admin → Functions, or rely on the copy in `deploy/mokliui/functions/`).
- Agent status strip above the main slot.

## Hidden

Notes, Workspace, Playground, Automations, Calendar, and Mokli Channels.
Personalization, Audio, direct Connections, and Tools settings tabs.

## Branding

`MOKLI_NAME` defaults to Mokli.
