# How to Use an AI Agent Mokli with mokli

mokli includes a browser Mokli for persistent chat sessions, visible agent
activity, workspace controls, Apps, MCP presets, Skills, settings, and
Automations.

## What you will build

- a local browser workbench
- one persistent chat session
- a visible timeline of agent messages, tool calls, and file edit diffs
- a gateway-backed WebSocket connection

## When to use this

Use the Mokli when you want a local AI agent interface that is easier to operate
than a terminal, especially for project work, file attachments, model switching,
workspace selection, Apps, Skills, and scheduled automations.

## Install

```bash
python -m pip install mokli-ai
mokli onboard --wizard
mokli agent -m "Hello!"
```

The published wheel already includes the Mokli bundle. You only need the
`mokli/` source directory when changing the frontend.

## Minimal working example

```bash
mokli mokli
```

The launcher checks setup, enables the local WebSocket channel after
confirmation, starts the gateway, and opens the browser.

When mokli edits a file, the Mokli activity timeline can show the changed
line counts, a unified diff, and an **Open file** action for a read-only
preview. File previews use the chat's current workspace access mode: restricted
access stays inside the selected workspace, while Full Access can preview files
outside the workspace when the gateway allows it.

## Production notes

- Use `mokli gateway --background` when you do not want to keep a terminal open, then open the
  configured Mokli URL in a browser.
- Use `mokli gateway status`, `logs`, `restart`, and `stop` to manage a
  background gateway.
- If you expose the Mokli beyond localhost, set a token issue secret and review
  workspace/tool access.

## Security notes

- The first-run Mokli path binds to `127.0.0.1` by default.
- Do not expose the Mokli on a LAN or public host without an intentional access
  model.
- Keep file and shell tools scoped to the workspace before inviting other users.

## Troubleshooting

- The Mokli is served by the WebSocket channel on port `8765` by default.
- The gateway health endpoint is separate from the browser UI.
- If the page opens but messages fail, check provider setup with
  `mokli agent -m "Hello!"`.

## Related mokli docs

- [Mokli Mokli](../mokli.md)
- [Quick Start](../quick-start.md)
- [WebSocket protocol](../websocket.md)
- [Configuration](../configuration.md)
