# tiny-ntfy-mcp

> [!IMPORTANT]
> **Deprecated and archived.** This MCP server has been retired in favour of a small Copilot CLI skill that calls `ntfy.sh` directly with `curl`. For a single user with anonymous publishing, the MCP machinery (worker thread, schema validation, sequence-ID tracking, on/off state) was over-engineering for what is, fundamentally, one HTTP POST.
>
> The replacement skill is reproduced below. Copy it into `~/.copilot/skills/ntfy-me/SKILL.md` (or your equivalent skills directory) and export `NTFY_TOPIC` from your shell profile.
>
> No further releases will be made. All open issues and PRs are closed.

## Replacement: `ntfy-me` Copilot CLI skill

`~/.copilot/skills/ntfy-me/SKILL.md`:

````markdown
---
name: ntfy-me
description: Send a single push notification to the user's phone via ntfy.sh. Use ONLY when the user explicitly says "ntfy me", "ntfy-me", "ntfy that ...", "ping my phone", or otherwise mentions ntfy by name. Do NOT use as a generic "task complete" notifier and do NOT auto-trigger from prompts like "let me know when done".
---

# ntfy-me

Anonymous publish to the user's pre-configured ntfy.sh topic. The topic lives in
`$NTFY_TOPIC`, exported by the user's shell profile (`.zshrc` on WSL/Linux,
PowerShell profile on Windows).

## Send

```bash
curl -fsS --max-time 5 -d "<message>" "https://ntfy.sh/$NTFY_TOPIC"
```

`<message>` is the plain-text body. Keep it short — this lands on a phone.

## Optional headers

Add only when the user asks for them or when the context clearly justifies it.
Pass each as `-H "<Name>: <value>"`.

| Header        | Use                                                        |
|---------------|------------------------------------------------------------|
| `Title`       | Short headline shown above the body.                       |
| `Priority`    | `min`, `low`, `default`, `high`, `max`, `urgent` (or 1-5). |
| `Tags`        | Comma-separated emoji shortcodes / labels.                 |
| `Click`       | URL opened when the notification is tapped.                |
| `Actions`     | One-tap buttons. Format: `view, <label>, <url>`.           |
| `Sequence-ID` | Stable id to update the same notification in place.        |
| `Markdown`    | `yes` to render the body as markdown.                      |

Example with title, priority, click, and update-in-place:

```bash
curl -fsS --max-time 5 \
  -H "Title: Build green" \
  -H "Priority: high" \
  -H "Tags: white_check_mark" \
  -H "Click: https://github.com/owner/repo/actions/runs/123" \
  -H "Sequence-ID: my-build" \
  -d "All checks passed in 1m42s." \
  "https://ntfy.sh/$NTFY_TOPIC"
```

## Don't

- Don't loop. One call per explicit user request.
- Don't auto-publish progress updates unless the user asked you to.
- Don't include secrets, tokens, full paths to sensitive files, or PII.
- Don't fall back to Bitwarden — `$NTFY_TOPIC` is already in the environment.
- Don't invent a topic. If `$NTFY_TOPIC` is empty, tell the user instead of guessing.
````

## Shell profile

WSL/Linux (`~/.zshrc` or equivalent):

```sh
export NTFY_TOPIC=your-topic-here
```

Windows PowerShell profile:

```powershell
$env:NTFY_TOPIC = 'your-topic-here'
```

## Removing the MCP

If you previously installed this MCP, remove it from your Copilot CLI config (`~/.copilot/mcp-config.json`) and from `mise` (or whichever package manager installed it):

```bash
mise uninstall "pipx:git+https://github.com/teh-hippo/tiny-ntfy-mcp.git"
```

## Final release

The last published version is `v2.0.12`. The historical `README` and full source are preserved in the git history.
