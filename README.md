# tiny-ntfy-mcp

Tiny local **MCP (stdio)** server exposing `ntfy_*` tools so agents can send fast, low-impact progress notifications via [ntfy](https://ntfy.sh/).

- **Fast ACK:** tool calls return immediately; delivery happens in the background.
- **Update-in-place:** by default, `ntfy_publish` sets `X-Sequence-ID` so progress updates edit a single notification instead of spamming.

## Quickstart

1. Pick a topic (e.g. `ntfy-my-random-topic`) and subscribe to it in the ntfy app.
2. Set `NTFY_TOPIC` (and auth if needed).
3. Add the MCP config below to Copilot CLI and restart it.

## Configuration

Config precedence:

1. Environment variables
2. `~/.env`
3. `~/.tiny-ntfy-mcp/config.json`

Required:

- `NTFY_TOPIC`

Optional:

- `NTFY_URL` (default: `https://ntfy.sh`)
- Auth: `NTFY_TOKEN` **or** `NTFY_USERNAME` + `NTFY_PASSWORD`
- `NTFY_MCP_ENABLED` = `1`/`0` (overrides persisted state)
- `NTFY_MCP_TIMEOUT_SEC` (default: `2`)
- `NTFY_MCP_DRY_RUN` = `1` (log publishes to stderr without sending)
- `NTFY_MCP_LOG_LEVEL` = `DEBUG|INFO|WARNING|ERROR` (default: `WARNING`)

Example `~/.tiny-ntfy-mcp/config.json`:

```json
{ "NTFY_TOPIC": "ntfy-my-random-topic" }
```

## Copilot MCP config

Add to `~/.copilot/mcp-config.json`:

```json
{
  "mcpServers": {
    "tiny-ntfy-mcp": {
      "type": "local",
      "command": "uv",
      "args": ["-q", "--no-progress", "--project", "/ABS/PATH/tiny-ntfy-mcp", "run", "-m", "tiny_ntfy_mcp"],
      "tools": ["*"]
    }
  }
}
```

Restart Copilot CLI, then call `ntfy_me` once. Use `ntfy_publish` during work (or let the model do it automatically after `ntfy_me`); call `ntfy_off` to stop.

## Tools

- `ntfy_me`: persistently enable notifications + opt into automatic progress publishing guidance
- `ntfy_off`: persistently disable notifications
- `ntfy_publish`: send a notification

If you used older command names, switch to `ntfy_me` and `ntfy_off`.

### ntfy_publish (recommended shape)

Minimal:

```json
{ "session": "build", "status": "progress", "result": "Running tests" }
```

Common fields:

- `stage` / `total`
- `result` / `next` / `details`
- `area` / `repo` / `branch` (added as tags: `area:<...>`, `repo:<...>`, `branch:<...>`)
- ntfy passthrough: `tags`, `priority`, `click`, `actions`, `icon`, `attach`, `filename`, `delay`, `email`, `markdown`
- `update` (default `true`) and `sequenceId` to control `X-Sequence-ID`

Inputs are schema-validated; unknown fields or invalid values return `-32602 Invalid params`.

## Windows notes

- `~/.env` is `$HOME\\.env` in PowerShell.
- Make sure `uv` is on `PATH` and the `--project` path matches where you cloned this repo.

## CI/CD (GitHub)

- Validate workflow runs ruff + pytest + `uv build`; optional live ntfy E2E runs when `NTFY_CI_TOPIC` secret is set.
- Release workflow uses `python-semantic-release` to create SemVer tags + GitHub Releases from Conventional Commits.
- Recommended repo settings: **rebase merges only**, auto-merge enabled, branch protection requiring the **Validate** check + linear history.
