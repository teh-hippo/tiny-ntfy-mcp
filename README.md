# tiny-ntfy-mcp

Tiny local **MCP (stdio)** server exposing `ntfy_*` tools so agents can send fast, low-impact progress notifications via [ntfy](https://ntfy.sh/).

- **Fast ACK:** tool calls return immediately; delivery happens in the background.
- **Update-in-place:** by default, `ntfy_publish` sets `X-Sequence-ID` so progress updates edit a single notification instead of spamming.

## Quickstart

1. Pick a topic (e.g. `ntfy-my-random-topic`) and subscribe to it in the ntfy app.
2. Set `NTFY_TOPIC` (and auth if needed).
3. Add the MCP config below to Copilot CLI and restart it.

## Configuration

Set `NTFY_TOPIC` (and auth if needed) via the MCP config `env` block (see below), environment variables, or `mise env`.

Required:

- `NTFY_TOPIC`

Optional:

- `NTFY_URL` (default: `https://ntfy.sh`)
- Auth: `NTFY_TOKEN` **or** `NTFY_USERNAME` + `NTFY_PASSWORD`
- `NTFY_MCP_ENABLED` = `1`/`0` (overrides in-session state)
- `NTFY_MCP_TIMEOUT_SEC` (default: `2`)
- `NTFY_MCP_DRY_RUN` = `1` (log publishes to stderr without sending)
- `NTFY_MCP_LOG_LEVEL` = `DEBUG|INFO|WARNING|ERROR` (default: `WARNING`)

## Copilot MCP config

Add to `~/.copilot/mcp-config.json`:

```json
{
  "mcpServers": {
    "tiny-ntfy-mcp": {
      "type": "local",
      "command": "uv",
      "args": ["-q", "--no-progress", "--project", "/ABS/PATH/tiny-ntfy-mcp", "run", "-m", "tiny_ntfy_mcp"],
      "env": {
        "NTFY_TOPIC": "your-topic-here"
      },
      "tools": ["*"]
    }
  }
}
```

Restart Copilot CLI, then call `ntfy_me` once. Use `ntfy_publish` during work (or let the model do it automatically after `ntfy_me`); call `ntfy_off` to stop.

## Tools

- `ntfy_me`: enable notifications + opt into automatic progress publishing guidance
- `ntfy_off`: disable notifications
- `ntfy_publish`: send a notification

### ntfy_publish (recommended shape)

Minimal:

```json
{ "session": "build", "status": "progress", "result": "Running tests" }
```

With action button (link to a PR diff):

```json
{
  "session": "build",
  "status": "success",
  "result": "PR #42 ready",
  "actions": "view, Open diff, https://github.com/org/repo/pull/42/files"
}
```

With image attachment:

```json
{
  "session": "deploy",
  "status": "success",
  "result": "Deployed to staging",
  "attach": "https://example.com/screenshot.png",
  "click": "https://staging.example.com"
}
```

Common fields:

- `stage` / `total`
- `result` / `next` / `details`
- `area` / `repo` / `branch` (added as tags: `area:<...>`, `repo:<...>`, `branch:<...>`)
- `click` — URL opened when notification is tapped (PR, diff, deployment, dashboard)
- `actions` — action buttons; semicolon-separated, e.g. `view, Open diff, https://github.com/org/repo/pull/1/files`
- `attach` — URL to an image or file displayed in the notification (screenshot, diagram, chart)
- `filename` — override the filename derived from the `attach` URL
- `icon` — URL to a JPEG/PNG image shown beside the notification
- other ntfy passthrough: `tags`, `priority`, `delay`, `email`, `markdown`
- `update` (default `true`) and `sequenceId` to control `X-Sequence-ID`

Inputs are schema-validated; unknown fields or invalid values return `-32602 Invalid params`.

## Windows notes

- Make sure `uv` is on `PATH` and the `--project` path matches where you cloned this repo.

## CI/CD (GitHub)

- Validate workflow runs ruff + pytest + `uv build`; optional live ntfy E2E runs when `NTFY_CI_TOPIC` secret is set.
- Release workflow uses `python-semantic-release` to create SemVer tags + GitHub Releases from Conventional Commits.
- Recommended repo settings: **rebase merges only**, auto-merge enabled, branch protection requiring the **Validate** check + linear history.
