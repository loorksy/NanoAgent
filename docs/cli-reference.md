# CLI Reference

Use this page when you know what you want to run and need the command shape. For a guided first run, start with [`quick-start.md`](./quick-start.md).

## Choose a Command

| Goal | Command | Notes |
|---|---|---|
| Check the install | `mokli --version` | If this fails, try `python -m mokli --version` |
| Create or refresh config | `mokli onboard` | Creates `~/.mokli/config.json` and `~/.mokli/workspace/` |
| Refresh config non-interactively | `mokli onboard --refresh` | Preserves existing values and adds missing default fields without prompting |
| Use guided setup | `mokli onboard --wizard` | Best when you prefer prompts over hand-editing JSON |
| Open the browser workbench | `mokli mokli` | Prepares local Mokli settings, starts the gateway, and opens the browser |
| Check readiness without calling a model | `mokli status` | Summarizes config/workspace and validates the active provider/model configuration |
| Send one test message | `mokli -m "Hello!"` | First proof that install, config, provider, model, and workspace all work |
| Chat in the terminal | `mokli` | Interactive local chat; `mokli agent` remains an explicit alias |
| Run the gateway directly | `mokli gateway` | Service/ops command for Mokli, chat apps, cron, and heartbeat |
| Deliver a local trigger | `mokli trigger <id> "message"` | Created first with `/trigger <name>` in the target chat/session |
| Serve an OpenAI-compatible API | `mokli serve` | Starts `/v1/chat/completions`, `/v1/models`, and `/health` |
| Check chat channel setup | `mokli channels status` | Useful before starting `mokli gateway` |
| Manage optional features | `mokli plugins list` | Shows channels and optional capabilities you can turn on |
| Log in to QR/OAuth-style channels | `mokli channels login <channel>` | Used by channels such as WhatsApp and WeChat |
| Log in to OAuth model providers | `mokli provider login <provider>` | Used by OpenAI Codex, xAI subscription, and GitHub Copilot providers |

## Global

```bash
mokli --help
mokli --version
python -m mokli --help
python -m mokli --version
```

`python -m mokli ...` is useful when the package is installed but the `mokli` script is not on `PATH`.

### Coexisting with Mokli Desktop

The Python package and Mokli Desktop keep separate runtimes, configuration,
workspaces, and state. When a running Desktop release publishes its private
terminal-access descriptor, an interactive bare `mokli` or `mokli mokli`
asks which installation to use after authenticating a ready Desktop target.
Use `Up`/`Down` to highlight an installation and `Enter` to confirm.
`Ctrl+C` cancels with exit code 130 without attaching to Desktop or starting a Python backend.
If Desktop is absent, busy, unavailable, or cannot be authenticated, the command
reports the current Python executable and continues normally. A virtual
environment's executable is shown without resolving it to its base interpreter.

Choosing Desktop for `mokli mokli` opens its already-running browser workbench
and exits; closing the browser never stops the Desktop gateway. Choosing Desktop
for bare `mokli` opens the terminal UI against that same running backend when
the Desktop host, gateway and terminal client support terminal protocol 1. Older
versions fail explicitly with update guidance. Use explicit `mokli agent` for
the original Python terminal UI.
After Desktop is selected, a disconnect or incompatible reply ends that invocation
with an error; it never silently switches to Python or launches a replacement.
On macOS, browser URLs are delivered through native Launch Services rather than
command-line arguments. A failed native handoff does not fall back to `open` or
a `BROWSER` command, keeping bootstrap credentials out of launcher arguments.

On Windows, the shared browser launcher uses a private HTML redirect rather than
passing a credential-bearing URL to a browser command. A short-lived, windowless
Python helper receives the URL over an anonymous pipe, opens the redirect through
the system's HTTP association, and attempts file cleanup after two minutes. The calling
CLI can exit immediately after the launch acknowledgement; this helper does not
start, stop, or keep a gateway alive. It does not honor `BROWSER` overrides.
Redirects are stored in the current user's Windows Local AppData known folder,
under `MokliBrowserHandoff-v1`, with an explicit current-user-only protected ACL.
An ACL-enforcing local filesystem and a non-reparse storage path are required;
unsafe existing storage or failed browser handoff fails without raw-URL fallback.
Abnormal termination can leave a private redirect behind. Later invocations retry
cleanup of verified redirect files older than ten minutes, excluding active files;
cleanup is not a guarantee of physical erasure or secrecy from same-user programs
or administrators. No Python/Desktop settings, credentials, or history are imported
between installations.

Any explicit subcommand or option—including `mokli agent`,
`mokli mokli --no-open`, config/workspace selectors, help, version, completion,
and gateway lifecycle commands—keeps its existing Python meaning and never opens
the Desktop picker. Target choices are not remembered, and Desktop settings are
not copied into the Python installation.

Desktop terminal credentials are short-lived WebSocket/API tokens obtained through
the authenticated current-user rendezvous. The TUI receives them through a bounded
anonymous pipe, not command arguments, environment variables or temporary files.
Its environment contains only a trusted resolver command and public instance IDs.
The resolver verifies the selected Desktop and gateway again for every credential
refresh. The gateway identity is also checked before any WebSocket mutation. This
mode does not acquire a gateway lifecycle lease: client exit leaves Desktop running,
and disconnect never automatically reconnects or replays an uncertain task.

Desktop-only distributions use the narrow `mokli-desktop-tui` entrypoint inside
their existing private runtime; it is not a replacement for the full Python CLI.
They must ship this engine entrypoint and a matching terminal client together.
The client cache can be kept inside Desktop's data root without reading or writing
the separate Python installation's config. No additional system Python is needed.

## Common Patterns

Most day-to-day commands use the default config and workspace. Advanced or multi-instance runs usually pass both paths explicitly:

```bash
mokli agent --config ./bot-a/config.json --workspace ./bot-a/workspace -m "Hello"
mokli gateway --config ./bot-a/config.json --workspace ./bot-a/workspace
mokli serve --config ./bot-a/config.json --workspace ./bot-a/workspace
```

Use `--verbose` on long-running processes when you need startup or runtime logs:

```bash
mokli gateway --verbose
mokli serve --verbose
```

Long-running commands keep working until you stop them. Press `Ctrl+C` in that terminal
to stop foreground `mokli gateway` or `mokli serve`. If you started the gateway
with `--background`, use `mokli gateway stop`.

## Setup

| Command | Description |
|---|---|
| `mokli onboard` | Initialize or refresh the default config and workspace |
| `mokli onboard --refresh` | Refresh an existing config without prompting, preserving existing values |
| `mokli onboard --wizard` | Use the interactive setup wizard |
| `mokli onboard --config <path> --workspace <path>` | Initialize or refresh a specific instance |

Default paths:

| Path | Default |
|---|---|
| Config | `~/.mokli/config.json` |
| Workspace | `~/.mokli/workspace/` |

## Status

| Command | Description |
|---|---|
| `mokli status` | Summarize the default config/workspace and check Agent provider/model readiness |
| `mokli status --config <path>` | Check a specific config file |
| `mokli status --workspace <path>` | Show status with a workspace override |

Status does not send a model request. On success, run the printed
`mokli agent -m "Hello!"` command to verify network access and credentials. On failure,
follow the printed Mokli **Settings → Models** or `mokli onboard --wizard` route.

## Agent CLI

| Command | Description |
|---|---|
| `mokli -m "Hello!"` | Send one message and exit |
| `mokli` | Start interactive terminal chat |
| `mokli --session <id>` | Use a WebSocket session key; add `--classic` for another channel |
| `mokli --workspace <path>` | Override workspace |
| `mokli --config <path>` | Use a specific config file |
| `mokli --classic` | Use the classic Python prompt instead of the native terminal UI |
| `mokli --theme auto\|dark\|light` | Auto-detect the terminal appearance or force a TUI palette |
| `mokli --no-markdown` | Use the classic prompt and print plain text instead of Markdown |
| `mokli --logs` | Use the classic prompt and show runtime logs while chatting |

Inside the native TUI, `/sessions` switches saved conversations, `/new-chat` starts another saved
conversation, and `/context` explains the compacted summary and raw session suffix available to
the next agent turn. `/branch` forks a saved conversation from a completed reply, and `/diff`
opens the latest turn's file changes as a full-screen unified diff.
`PageUp` loads older transcript pages when you reach the top. By default, each launch starts a
new session using the launch directory as its workspace. `--session` selects a specific existing
session, and `--workspace` overrides the launch directory. When the TUI exits, it prints a
ready-to-run `mokli agent --session ...` command for the current session.

## Session Storage and Rollback

Session JSONL files live under `<config-dir>/sessions/<workspace-id>/`, outside the
agent-readable workspace. On the first upgraded start, mokli safely migrates existing
`<workspace>/sessions/*.jsonl` files after verifying an atomic copy. Stop every old mokli
process that uses the workspace before upgrading; old and new binaries must not write the
same session concurrently.

To prepare a downgrade, stop mokli and copy the current sessions back to the path understood
by older releases:

```bash
mokli sessions restore-workspace --config ./bot-a/config.json --workspace ./bot-a/workspace
```

The command never deletes the external store and refuses to overwrite a different existing
workspace file. Back up both the config directory and workspace before changing versions.

Interactive mode uses mokli's native TypeScript terminal UI. It talks to the same local gateway as the Mokli, so streaming, tool progress, and WebSocket sessions share one protocol instead of maintaining a second agent loop. If no gateway is running, either client starts it on demand. The TUI paints immediately while the local gateway starts, then obtains fresh bootstrap credentials and connects in the background. Exiting one TUI or Mokli launcher releases only that client; the last interactive launcher stops the on-demand gateway. A small gateway watchdog also reclaims an on-demand process if its last client crashes. `/detach` promotes the shared gateway to persistent background mode before closing the TUI, so active agent work continues without a connected client. An explicit `mokli gateway --background` starts or promotes the gateway the same way before opening a client. `mokli gateway restart` restarts a detached gateway without changing that lifetime; restart an attached foreground gateway in its owning terminal. `mokli gateway stop` ends either mode.

The default `--theme auto` mode paints first with the terminal's default background, probes the real foreground and background colors asynchronously, and follows supported live appearance changes. Use `--theme light` or `--theme dark` when a terminal or multiplexer does not report its colors reliably. The model preset and workspace access labels above the composer can be clicked to open their selectors; arrow keys, `Enter`, and `Esc` provide the same controls without a mouse. Access changes still pass through the gateway's local-trust and active-turn policy checks.

`Enter` sends the current message. While mokli is working, `Enter` sends immediately, `Tab` waits until the current response is finished, and `Option+Up` on macOS (`Alt+Up` on Windows/Linux) returns the latest waiting message to the composer. Press `Shift+Enter` to add a newline; `Ctrl+J` is the universal fallback when a terminal cannot distinguish modified Enter keys. `Alt+Enter` and `Ctrl+Enter` are also accepted when distinguishable. Use `Up`/`Down` at the composer edge to recall prompts from the current saved session. Large pastes appear as a compact placeholder in the composer but are sent unchanged. Type `/` to discover mokli commands and terminal navigation in one palette, or type `@` to complete installed apps, configured MCP servers, and saved sessions. Use the arrow keys to choose an item and `Tab` to complete it. `/sessions` opens a searchable conversation picker, `/new-chat` preserves the current conversation and starts another one, and `/branch` forks from a completed reply. `/diff` opens a read-only unified diff for the newest turn; use `Left`/`Right` to switch edits and `Esc` to close it. The core `/new` command retains its cross-channel behavior and resets the current chat. `Ctrl+C` copies a selection, stops a running turn, clears a non-empty composer, or exits when idle. Use `PageUp`/`PageDown` to scroll, `Ctrl+Home`/`Ctrl+End` to jump to the transcript edges, and `Ctrl+O` to expand or collapse long tool traces. When you leave the bottom, the TUI shows a scrollbar and a `Ctrl+End` hint until you return. The footer reports provider token/cache usage when available. Selections copy through OSC 52 when the terminal supports it. The transcript reflows when the terminal is resized, and exiting restores the previous screen.

Packaged releases fetch a version-matched, checksummed terminal archive for macOS (Apple Silicon and Intel), Linux (x64 and ARM64), or Windows x64 on first use. The cache keeps the executable together with its licenses, third-party notices, source offer, relinking instructions, and corresponding TUI source. Windows ARM64 currently falls back to the classic prompt because the Bun runtime disables the FFI required by OpenTUI on that platform. Set `MOKLI_TUI_NO_DOWNLOAD=1` or pass `--classic` to keep the Python-only path. A local source install requires Bun and runs its own `tui/` source while the original checkout remains available; it never silently falls back to a release binary.

Non-interactive input/output, `--logs`, and `--no-markdown` automatically retain the classic prompt so existing scripts and diagnostic workflows do not acquire terminal control sequences or silently ignore their options.

Interactive mode exits with `exit`, `quit`, `/exit`, `/quit`, `:q`, or `Ctrl+D`. Use `/detach` instead to close the TUI without stopping the shared gateway or its active agent work. The restored terminal prints a copyable stop command with the same `--config` and explicit `--workspace` selectors.

## Mokli

| Command | Description |
|---|---|
| `mokli mokli` | Create config/workspace if needed, enable the local Mokli channel after confirmation, start the gateway, open `http://127.0.0.1:8765`, and follow new gateway logs |
| `mokli mokli --background` | Deprecated; prints the equivalent explicit `mokli gateway --background` command and exits |
| `mokli mokli --dev` | Start the gateway and Vite together at `http://127.0.0.1:5173`, with live frontend updates |
| `mokli mokli --no-open` | Prepare and start the Mokli without opening a browser |
| `mokli mokli --port <port>` | Set the Mokli/WebSocket port |
| `mokli mokli --gateway-port <port>` | Override the gateway health port |
| `mokli mokli --yes` | Apply safe localhost Mokli defaults without confirmation; configure provider credentials in **Settings → Models** |

First-run Mokli setup binds to `127.0.0.1` by default. Use manual configuration and a Mokli password before exposing the WebSocket channel beyond localhost.

`--dev` is a foreground source-checkout workflow. Persistent gateway lifecycle is deliberately
owned only by `mokli gateway --background`; `mokli mokli --background` prints migration
guidance instead of silently changing process ownership.
It installs frontend dependencies when `mokli/node_modules` is missing, proxies to the configured
WebSocket channel port, and stops Vite when the launcher exits. The shared on-demand gateway stops
only when no other interactive client still holds it.

## Gateway

`mokli gateway` starts enabled chat channels, Mokli/WebSocket when configured, cron-backed system jobs, Dream, heartbeat, and the health endpoint. Most local browser users should start with `mokli mokli`; use `gateway` directly for service management, chat app operation, and advanced deployment. By default it runs in the foreground, which keeps existing scripts and terminal workflows unchanged. Use `--background` when you want a local macOS, Linux, or Windows process that you can manage from the CLI.

| Command | Description |
|---|---|
| `mokli gateway` | Start the gateway in the foreground with config defaults |
| `mokli gateway --verbose` | Show verbose runtime output |
| `mokli gateway --port <port>` | Override `gateway.port` for the health endpoint |
| `mokli gateway --workspace <path>` | Override workspace |
| `mokli gateway --config <path>` | Use a specific config file |
| `mokli gateway --background` | Start the gateway as a background process |
| `mokli gateway status` | Show PID, foreground/background launch mode, explicit/on-demand lifetime, live client count, state, and logs |
| `mokli gateway logs --no-follow` | Print recent background gateway logs and exit |
| `mokli gateway logs` | Follow background gateway logs |
| `mokli gateway restart` | Restart the recorded background gateway with the current config |
| `mokli gateway stop` | Stop the recorded background gateway |
| `mokli gateway install-service` | Install a systemd user service or macOS LaunchAgent |
| `mokli gateway install-service --dry-run` | Preview the generated service file and system commands |
| `mokli gateway uninstall-service` | Remove the installed system service |

For custom instances, pass the same selector flags to management commands:

```bash
mokli gateway --background --config ./bot-a/config.json --workspace ./bot-a/workspace
mokli gateway status --config ./bot-a/config.json --workspace ./bot-a/workspace
mokli gateway stop --config ./bot-a/config.json --workspace ./bot-a/workspace
mokli gateway install-service --config ./bot-a/config.json --workspace ./bot-a/workspace --name bot-a
```

`--background` is a lightweight detached process. `install-service` is for
login/startup integration: Linux uses a systemd user service; macOS uses a
LaunchAgent plist. System services run the foreground gateway under the OS
supervisor rather than nesting another background process.

Default health endpoint:

```text
http://127.0.0.1:18790/health
```

The bundled Mokli is served by the WebSocket channel, usually on port `8765`, not by the gateway health endpoint.

## Local Triggers

`mokli trigger` delivers one local message to a trigger that was created from
a chat/session with `/trigger <name>`.

```bash
mokli trigger trg_8K4P2Q9X "Review PR #4502"
```

Keep `mokli gateway` running so the message can be delivered to the linked
chat/session. The message is recorded as an automation turn in that session,
not as a normal chat message typed by the user.

The command writes to a workspace-local durable queue. If `mokli gateway` is
not running yet, the message waits in that workspace. If the target session is
already running a turn, the trigger waits for that session to become idle. If the
gateway exits after claiming a delivery but before the linked turn completes,
the next gateway start requeues that delivery. The queue is at-least-once, not
exactly-once, so the same message can be delivered again after an interrupted
process. If the agent receives the delivery and the turn fails, the delivery is
marked failed instead of retried indefinitely. Each delivery also writes an
audit record under `<workspace>/triggers/runs`. Run one gateway consumer per
workspace; this local queue is not a distributed multi-consumer queue.

Use stdin when another local process generates the message:

```bash
generate-report | mokli trigger trg_8K4P2Q9X
```

Options:

| Command | Description |
|---|---|
| `mokli trigger <id> "message"` | Deliver one message through a trigger |
| `mokli trigger <id>` | Read the message from stdin |
| `mokli trigger --config <path> <id> "message"` | Use the workspace from a specific config |
| `mokli trigger --workspace <path> <id> "message"` | Use a specific workspace |

Triggers are managed in the Mokli Automations view instead of through separate
`list`, `revoke`, or `delete` CLI subcommands. From there you can pause/resume,
rename, delete, search, and copy the command for each trigger.

For webhooks or other external systems, run your own small service and have it
call this CLI after it decides what message mokli should receive.

See [Automations](./automations.md) for the broader automation model, Mokli
management, and delivery behavior.

## OpenAI-Compatible API

| Command | Description |
|---|---|
| `mokli serve` | Start `/v1/chat/completions`, `/v1/models`, and `/health` |
| `mokli serve --host <host>` | Override API bind host |
| `mokli serve --port <port>` | Override API port |
| `mokli serve --timeout <seconds>` | Override per-request timeout |
| `mokli serve --verbose` | Show runtime logs |
| `mokli serve --workspace <path>` | Override workspace |
| `mokli serve --config <path>` | Use a specific config file |

Default API endpoint:

```text
http://127.0.0.1:8900
```

Public binds (`0.0.0.0` or `::`) require `api.apiKey`; send it as a Bearer token on API routes.

See [`openai-api.md`](./openai-api.md) for request examples.

## Status

```bash
mokli status
```

Shows the config path, workspace path, active model, and provider summary without calling a model.

| Command | Description |
|---|---|
| `mokli status` | Inspect the default instance |
| `mokli status --config <path>` | Inspect a specific config |
| `mokli status --config <path> --workspace <path>` | Inspect a specific config with a workspace override |

## Channels

| Command | Description |
|---|---|
| `mokli channels status` | Show configured channel status |
| `mokli channels status --config <path>` | Show channel status for a specific config |
| `mokli channels login <channel>` | Run interactive login for supported channels |
| `mokli channels login <channel> --force` | Re-authenticate even if credentials already exist |
| `mokli channels login <channel> --config <path>` | Use a specific config file |
| `mokli plugins list --config <path>` | Show plugin/channel enabled state for a specific config |

Examples:

```bash
mokli channels login whatsapp
mokli channels login weixin
mokli channels status
```

See [`chat-apps.md`](./chat-apps.md) for channel-specific setup.

## Optional Features

Use these commands when you want mokli to add or remove a built-in capability
without hand-editing JSON. Enabling may install the support package first.
Disabling is for channels such as Telegram, Matrix, or Slack; it keeps your
saved settings and turns the channel off.

The `plugins` command name is retained for compatibility, but these entries are
mokli runtime support packages, not the user-invokable tools shown in Mokli
Apps. They cannot be attached to a chat turn with `@`.

| Feature name | What it enables |
|---|---|
| `api` | Dependencies required by the OpenAI-compatible `mokli serve` process |
| `azure` | Azure identity support for Azure-hosted models |
| `bedrock` | AWS Bedrock model provider support |
| `langfuse` | Langfuse tracing support for OpenAI-compatible providers |
| `olostep` | Olostep web search provider support |
| A channel name such as `telegram` or `slack` | The connector package and saved channel enablement |

| Command | Description |
|---|---|
| `mokli plugins list` | Show available channels and optional capabilities |
| `mokli plugins enable <name>` | Install missing support and enable the feature or channel |
| `mokli plugins enable <name> --logs` | Show package install logs while enabling |
| `mokli plugins disable <channel>` | Turn off a channel without deleting its saved settings |
| `mokli plugins list --config <path>` | Read a specific config file |
| `mokli plugins enable <name> --config <path>` | Update a specific config file |
| `mokli plugins disable <channel> --config <path>` | Turn off a channel in a specific config file |

Document and PDF reading are included in the standard installation. The old
`mokli plugins enable documents` and `mokli plugins enable pdf` commands
remain accepted as no-op compatibility aliases.

## Provider OAuth

| Command | Description |
|---|---|
| `mokli provider login openai-codex --set-main` | Authenticate Codex and select its current default model |
| `mokli provider login xai-grok --set-main` | Authenticate an eligible X Premium / Grok subscription and select Grok 4.6; hosted X Search is enabled for models that advertise support |
| `mokli provider login github-copilot --set-main` | Authenticate GitHub Copilot and select its current default model |
| `mokli provider logout openai-codex` | Remove OpenAI Codex OAuth state |
| `mokli provider logout xai-grok --config <path>` | Remove the selected mokli instance's xAI OAuth state |
| `mokli provider logout github-copilot` | Remove GitHub Copilot OAuth state |

See [`providers.md`](./providers.md#oauth-providers) for when OAuth providers need explicit provider/model selection.

## Useful First Checks

```bash
mokli --version
mokli status
mokli agent -m "Hello!"
```

If these fail, use [`troubleshooting.md`](./troubleshooting.md) before debugging Mokli, chat apps, Docker, systemd, or SDK integrations.
