# Build a Feishu AI Agent with mokli

This guide connects mokli to Feishu or Lark through the `feishu` channel. The
channel uses a WebSocket long connection, so the first setup does not require a
public webhook URL.

## What this guide builds

- a Feishu/Lark bot app connected to mokli
- the `feishu` channel enabled in `config.json`
- one pairing-approved Feishu or Lark user
- mention-only group behavior for first deployment

## Prerequisites

- A working local mokli reply:

```bash
mokli agent -m "Hello!"
```

- A Feishu or Lark account that can create or approve bot apps.
- Permission to run `mokli gateway` continuously.

## Install mokli

```bash
python -m pip install mokli-ai
mokli onboard --wizard
```

## Enable the Feishu channel

Install the optional channel dependency:

```bash
mokli plugins enable feishu
```

The easiest path is QR login:

```bash
mokli channels login feishu
```

Open the printed URL or scan the QR code. mokli writes the generated `appId`,
`appSecret`, `domain`, and `enabled` fields into the active config.

If QR login is unavailable, create a Feishu/Lark app manually and merge this
shape into `~/.mokli/config.json`:

```json
{
  "channels": {
    "feishu": {
      "enabled": true,
      "appId": "cli_xxx",
      "appSecret": "xxx",
      "groupPolicy": "mention",
      "streaming": true,
      "domain": "feishu"
    }
  }
}
```

Omitting `allowFrom` enables pairing-only mode. A new user should DM the bot,
get a pairing code, and be approved before using the bot normally.

For manual apps, enable the Bot capability, receive-message events, and Long
Connection mode. If your app cannot get the `cardkit:card:write` permission,
set `"streaming": false`.

## Run mokli gateway

```bash
mokli channels status
mokli gateway
```

## Test a message

DM the bot first. It should return a pairing code. Approve it from a trusted
local surface:

```bash
mokli agent -m "/pairing approve ABCD-EFGH"
```

After approval, DM the bot again or mention it in a group chat:

```text
@mokli Hello from Feishu
```

## Security notes

- Prefer pairing-only mode for first setup. Add `allowFrom` only when you want a
  static allowlist.
- Keep `groupPolicy` as `"mention"` before inviting the bot into busy groups.
- Store app secrets through environment variables for deployed services.
- Review file, shell, and web tool access before adding more users.

## Troubleshooting

- If QR login is unavailable, use manual app setup from the full chat-apps
  reference.
- If streaming cards fail, confirm `cardkit:card:write` or set
  `"streaming": false`.
- If no messages arrive, check Feishu/Lark event permissions, Long Connection
  mode, and `mokli gateway --verbose`.
- If a first DM returns a pairing code, approve it before testing normal
  replies.

## Next: memory, automations, MCP tools

- [Chat Apps reference](../chat-apps.md)
- [Pairing](../configuration.md#pairing)
- [AI Agent Memory](./ai-agent-memory.md)
- [Configure MCP tools](./configure-mcp-tools.md)
