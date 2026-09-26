# How to Configure MCP Tools in mokli

This guide adds an MCP server to mokli so the agent can use external tools
through the Model Context Protocol.

## What you will build

- a working mokli agent
- one MCP integration configured through Apps or `~/.mokli/config.json`
- a restricted set of MCP tools exposed to the model

## When to use this

Use MCP when the capability you need already exists as an MCP server, or when
you want external tools to be managed outside mokli core.

## Install

```bash
python -m pip install mokli-ai
mokli onboard --wizard
mokli agent -m "Hello!"
```

Install the MCP server runtime separately. Many examples use `npx`, `uvx`, or a
remote HTTP endpoint.

## Minimal working example

For local interactive setup:

1. Run `mokli mokli` and open **Apps**.
2. Choose a known MCP server preset, or add a custom stdio, HTTP, or SSE server.
   For a custom OAuth server, choose **OAuth** under **Authentication**, save it,
   and click **Connect**. Presets such as Xmind, Notion, and Linear go straight to
   **Connect**. Approve access in the browser window. HTTPS and localhost Moklis
   return automatically. From a remote plain-HTTP Mokli, copy the complete
   localhost callback URL from the browser address bar and paste it into mokli.
3. Limit the enabled tools when the server exposes more than the task needs.
4. Save and restart when prompted.
5. Mention the connected MCP server with `@` in the next message and ask for a small test action.

For manual or deployment-managed config, add this to `~/.mokli/config.json`:

```json
{
  "tools": {
    "mcpServers": {
      "filesystem": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"],
        "enabledTools": ["read_file"]
      }
    }
  }
}
```

Restart mokli and ask a question that requires the MCP tool.

## Production notes

- Prefer `enabledTools` over exposing every tool by default.
- Use `toolTimeout` for slow MCP operations.
- Use HTTP MCP only for endpoints you trust.
- For deployment-managed OAuth servers, set `auth` to `oauth` and complete the
  browser connection from **Apps → MCP**.
- Keep MCP server commands stable and versioned in deployment docs or scripts.

## Security notes

- Stdio MCP starts a local process; review the command before enabling it.
- HTTP/SSE MCP uses mokli's SSRF guard, including OAuth discovery, registration,
  token exchange, and redirects.
- OAuth credentials live in the mokli data directory, not in `config.json`.
- Allow private HTTP MCP hosts only with narrow `tools.ssrfWhitelist` CIDRs.
- Do not place secrets in command arguments when environment variables or
  headers can be used.

## Troubleshooting

- Run the MCP command outside mokli first.
- Start `mokli gateway --verbose` and inspect tool registration logs.
- If an HTTP MCP URL is blocked, check whether it points to loopback or a
  private address that needs explicit allowlisting.

## Related mokli docs

- [MCP tools for AI agents](./mcp-tools-for-ai-agents.md)
- [Configuration: MCP](../configuration.md#mcp-model-context-protocol)
- [Security](../configuration.md#security)
