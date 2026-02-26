from __future__ import annotations

import base64
import logging
import os
import queue
import re
import secrets
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from email.header import Header
from typing import Any

import anyio
import jsonschema
import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.shared.exceptions import McpError

_STATUS_TAG = dict(progress="loudspeaker", success="heavy_check_mark", warning="warning", error="rotating_light", info="information_source")
_STATUS_PRIORITY = dict(progress="low", info="default", success="high", warning="high", error="urgent")

_LOG = logging.getLogger("tiny-ntfy-mcp")


def _configure_logging() -> None:
    if _LOG.handlers:
        return

    raw_level = (os.getenv("NTFY_MCP_LOG_LEVEL") or "").strip().upper()
    if raw_level in {"", "0", "OFF", "NONE"}:
        level = logging.WARNING
    elif raw_level.isdigit():
        level = int(raw_level)
    else:
        level = {
            "CRITICAL": logging.CRITICAL,
            "ERROR": logging.ERROR,
            "WARN": logging.WARNING,
            "WARNING": logging.WARNING,
            "INFO": logging.INFO,
            "DEBUG": logging.DEBUG,
        }.get(raw_level, logging.WARNING)

    h = logging.StreamHandler(sys.stderr)
    h.setFormatter(logging.Formatter("[tiny-ntfy-mcp] %(levelname)s: %(message)s"))
    _LOG.addHandler(h)
    _LOG.setLevel(level)
    _LOG.propagate = False


_configure_logging()

# Copilot CLI validates tool schemas strictly and currently expects `"type": "object"`.
_EMPTY_OBJ_SCHEMA: dict[str, Any] = {"type": "object", "properties": {}, "additionalProperties": False}
_PUBLISH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "session": {"type": "string", "minLength": 1, "description": "Logical session/task name."},
        "stage": {"type": "integer", "minimum": 0, "description": "Progress stage (e.g. 2)."},
        "total": {"type": "integer", "minimum": 0, "description": "Total stages (e.g. 5)."},
        "status": {
            "type": "string",
            "enum": ["progress", "success", "warning", "error", "info"],
            "description": "Drives default tags/priority.",
        },
        "result": {"type": "string", "description": "Short result line."},
        "next": {"type": "string", "description": "Suggested next step."},
        "details": {"type": "string", "description": "Extra multi-line details."},
        "area": {"type": "string", "description": "Work area (becomes a tag: area:<...>)."},
        "repo": {"type": "string", "description": "Repo name (becomes a tag: repo:<...>)."},
        "branch": {"type": "string", "description": "Branch name (becomes a tag: branch:<...>)."},
        "title": {"type": "string", "description": "ntfy title (X-Title)."},
        "message": {"type": "string", "description": "ntfy body/message."},
        "tags": {
            "description": "Comma-separated string or array of tag strings.",
            "anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}],
        },
        "priority": {
            "description": "ntfy priority (1-5 or min/low/default/high/max/urgent).",
            "anyOf": [
                {"type": "integer", "minimum": 1, "maximum": 5},
                {"type": "string", "enum": ["1", "2", "3", "4", "5", "min", "low", "default", "high", "max", "urgent"]},
            ],
        },
        "update": {"type": "boolean", "default": True, "description": "When true, sets X-Sequence-ID to update one notification."},
        "sequenceId": {"type": "string", "description": "Explicit X-Sequence-ID (overrides auto-generated)."},
        "topic": {"type": "string", "description": "Override the configured ntfy topic for this call."},
        "markdown": {"type": "boolean", "description": "Enable ntfy markdown rendering (X-Markdown)."},
        "click": {"type": "string", "description": "ntfy click URL (X-Click). URL opened when notification is tapped. Use for linking to diffs, PRs, deployments, dashboards, or any relevant page."},
        "actions": {
            "type": "string",
            "description": "ntfy action buttons (X-Actions). Semicolon-separated. Format per action: 'view, <label>, <url>' or 'http, <label>, <url>[, method=<m>][, body=<b>]'. Example: 'view, Open diff, https://github.com/org/repo/pull/1/files; view, Dashboard, https://app.example.com'. Use to give the operator one-tap access to relevant URLs.",
        },
        "icon": {"type": "string", "description": "ntfy icon URL (X-Icon). URL to a JPEG/PNG image shown beside the notification."},
        "attach": {"type": "string", "description": "ntfy attachment URL (X-Attach). URL to an image or file displayed in the notification. Use for screenshots, architecture diagrams, charts, or any visual that helps the operator understand context."},
        "filename": {"type": "string", "description": "Filename for attachment (X-Filename). Overrides the filename derived from the attach URL."},
        "email": {"type": "string", "description": "Forward via email (X-Email)."},
        "delay": {"anyOf": [{"type": "string"}, {"type": "number"}], "description": "Delay delivery (X-Delay)."},
    },
    "required": ["session"],
}


def _tool_def(name: str, title: str, description: str, input_schema: dict[str, Any]) -> types.Tool:
    return types.Tool(name=name, title=title, description=description, inputSchema=input_schema)


_PRIMARY_TOOLS = [
    _tool_def(
        "ntfy_me",
        "Enable notifications",
        "Enable notifications and opt into automatic progress updates.",
        _EMPTY_OBJ_SCHEMA,
    ),
    _tool_def("ntfy_off", "Disable notifications", "Disable notifications.", _EMPTY_OBJ_SCHEMA),
    _tool_def(
        "ntfy_publish",
        "Publish notification",
        "Publish a progress/completion notification (fast ACK; delivery is background). Include 'click' or 'actions' to link the operator to relevant URLs (PRs, diffs, deployments). Include 'attach' for images or visual context.",
        _PUBLISH_SCHEMA,
    ),
]
_TOOL_DEFS = _PRIMARY_TOOLS
_TOOL_BY_NAME = {t.name: t for t in _TOOL_DEFS}


def _parse_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    v = value.strip().lower()
    if v in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if v in {"0", "false", "f", "no", "n", "off"}:
        return False
    return None


def _redact(value: str | None, *, keep_end: int = 4) -> str | None:
    if value is None:
        return None
    if len(value) <= keep_end:
        return "*" * len(value)
    return ("*" * (len(value) - keep_end)) + value[-keep_end:]


@dataclass(frozen=True)
class NtfyConfig:
    url: str
    topic: str
    token: str | None
    username: str | None
    password: str | None
    timeout_sec: float
    dry_run: bool

    @property
    def endpoint(self) -> str:
        base = self.url.strip().rstrip("/")
        if not base.startswith(("http://", "https://")):
            base = "https://" + base
        topic = self.topic.strip().lstrip("/")
        return f"{base}/{topic}"


def _load_ntfy_config() -> NtfyConfig | None:
    def get(key: str) -> str | None:
        v = os.environ.get(key)
        return v if isinstance(v, str) else None

    def get_float(key: str, default: float) -> float:
        raw = get(key)
        if raw is None:
            return default
        try:
            return float(raw)
        except ValueError:
            return default

    def get_bool(key: str, default: bool) -> bool:
        parsed = _parse_bool(get(key))
        return default if parsed is None else parsed

    topic = get("NTFY_TOPIC")
    if not topic:
        return None

    return NtfyConfig(
        url=get("NTFY_URL") or "https://ntfy.sh",
        topic=topic,
        token=get("NTFY_TOKEN"),
        username=get("NTFY_USERNAME"),
        password=get("NTFY_PASSWORD"),
        timeout_sec=get_float("NTFY_MCP_TIMEOUT_SEC", 2.0),
        dry_run=get_bool("NTFY_MCP_DRY_RUN", False),
    )


def _auth_header(cfg: NtfyConfig) -> str | None:
    if cfg.token:
        return f"Bearer {cfg.token}"
    if cfg.username and cfg.password:
        raw = f"{cfg.username}:{cfg.password}".encode()
        return "Basic " + base64.b64encode(raw).decode("ascii")
    return None


def _http_header_value(value: str) -> str:
    # Python's stdlib HTTP stack requires header values to be latin-1 encodable.
    # ntfy supports UTF-8 headers, but not all clients/libraries do; docs recommend RFC 2047.
    try:
        value.encode("latin-1")
        return value
    except UnicodeEncodeError:
        return Header(value, "utf-8", maxlinelen=0).encode(maxlinelen=0, linesep="")


def _sanitize_tag(value: str) -> str:
    v = "-".join(value.strip().split())
    v = v.replace(",", "-")
    # Keep tags short and reasonably URL/path friendly (sequence IDs may also be used in URL paths).
    v = re.sub(r"[^A-Za-z0-9._:/-]+", "-", v)
    return v[:64] if len(v) > 64 else v


def _ntfy_publish(cfg: NtfyConfig, *, message: str, headers: dict[str, str]) -> None:
    title = headers.get("X-Title") or headers.get("Title")
    if cfg.dry_run:
        redacted_topic = _redact(cfg.topic) or "<redacted>"
        _LOG.info(
            "[dry-run] publish to %s/%s title=%r chars=%d headers=%s",
            cfg.url.rstrip("/"),
            redacted_topic,
            title,
            len(message),
            ",".join(sorted(headers)),
        )
        return

    headers = {
        "User-Agent": "tiny-ntfy-mcp/0.1.0",
        "Content-Type": "text/plain; charset=utf-8",
        **headers,
    }
    # Never allow callers to smuggle an Authorization header.
    headers.pop("Authorization", None)
    if (auth := _auth_header(cfg)) is not None:
        headers["Authorization"] = auth

    headers = {k: _http_header_value(v) for k, v in headers.items()}
    req = urllib.request.Request(
        cfg.endpoint,
        data=message.encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=cfg.timeout_sec) as resp:
        # Drain a small amount to ensure request completes; body is not needed.
        resp.read(1)


@dataclass
class DeliveryStats:
    last_success_at: float | None = None
    last_error_at: float | None = None
    last_error: str | None = None
    sent_ok: int = 0
    sent_err: int = 0


class NtfyWorker:
    def __init__(self, cfg: NtfyConfig, *, max_queue: int = 200) -> None:
        self._cfg = cfg
        self._q: queue.Queue[tuple[NtfyConfig, dict[str, str], str]] = queue.Queue(maxsize=max_queue)
        self._stats = DeliveryStats()
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._run, name="tiny-ntfy-mcp-worker", daemon=True)
        self._t.start()

    @property
    def stats(self) -> DeliveryStats:
        return self._stats

    @property
    def queue_size(self) -> int:
        return self._q.qsize()

    def enqueue_with_cfg(self, cfg: NtfyConfig, *, headers: dict[str, str], message: str) -> None:
        self._q.put_nowait((cfg, headers, message))

    def close(self) -> None:
        # Best-effort flush: give the worker a brief chance to send queued notifications
        # before shutting down (shutdown is typically when the MCP client exits).
        deadline = time.time() + 1.0
        while time.time() < deadline and not self._q.empty():
            time.sleep(0.01)
        self._stop.set()
        try:
            self._q.put_nowait((self._cfg, {}, ""))
        except queue.Full:
            pass
        self._t.join(timeout=1.0)

    def _run(self) -> None:
        while not self._stop.is_set():
            cfg, headers, message = self._q.get()
            if self._stop.is_set():
                break
            if not headers and not message:
                continue
            try:
                _ntfy_publish(cfg, message=message, headers=headers)
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                self._stats.sent_err += 1
                self._stats.last_error_at = time.time()
                self._stats.last_error = f"{type(e).__name__}: {e}"
            else:
                self._stats.sent_ok += 1
                self._stats.last_success_at = time.time()


class NtfyMcpServer:
    def __init__(self) -> None:
        self._enabled_state = False
        self._ntfy_cfg = _load_ntfy_config()
        self._worker = NtfyWorker(self._ntfy_cfg) if self._ntfy_cfg else None
        self._forced_sequence_id = os.getenv("NTFY_MCP_SEQUENCE_ID")
        self._sequence_ids: dict[str, str] = {}

    def close(self) -> None:
        if self._worker:
            self._worker.close()

    def call_tool(self, name: str, args: dict[str, Any] | None) -> types.CallToolResult:
        args = {} if args is None else args
        if name == "ntfy_me":
            return self._tool_me()
        if name == "ntfy_off":
            return self._tool_set_enabled(False)
        if name == "ntfy_publish":
            return self._tool_publish(args)
        raise ValueError(f"Unknown tool: {name}")

    # --- Tools ---

    def _effective_enabled(self) -> bool:
        forced = _parse_bool(os.getenv("NTFY_MCP_ENABLED"))
        return self._enabled_state if forced is None else forced

    def _tool_set_enabled(self, enabled: bool) -> types.CallToolResult:
        self._enabled_state = enabled
        return _tool_result(f"ntfy: {'enabled' if enabled else 'disabled'}", {"enabled": enabled})

    def _tool_me(self) -> types.CallToolResult:
        self._enabled_state = True
        return _tool_result(
            "ntfy: enabled via ntfy_me; use ntfy_publish at start, milestones, blockers/errors, and completion",
            {
                "enabled": True,
                "publishCadence": ["start", "milestone", "blocker_or_error", "completion"],
            },
        )

    def _tool_publish(self, args: dict[str, Any]) -> types.CallToolResult:
        if not self._effective_enabled():
            return _tool_result(
                "ntfy: disabled (dropped)",
                {"enabled": False, "enqueued": False, "reason": "disabled"},
            )

        cfg = self._ntfy_cfg
        if not cfg:
            return _tool_result(
                "ntfy: missing NTFY_TOPIC (set via env)",
                {"configured": False},
                is_error=True,
            )

        session = args.get("session")
        if not isinstance(session, str) or not (session := session.strip()):
            raise ValueError("ntfy_publish: session must be a non-empty string")

        stage, total = args.get("stage"), args.get("total")
        result, next_step, details = args.get("result"), args.get("next"), args.get("details")
        repo, area, branch = args.get("repo"), args.get("area"), args.get("branch")
        raw_status = args.get("status")
        status = raw_status.strip().lower() if isinstance(raw_status, str) and raw_status.strip() else "progress"
        if status not in _STATUS_TAG:
            raise ValueError("ntfy_publish: status must be one of: progress, success, warning, error, info")

        tags = args.get("tags")
        user_tags: list[str] = []
        if isinstance(tags, str):
            user_tags = [t.strip() for t in tags.split(",") if t.strip()]
        elif isinstance(tags, list):
            for item in tags:
                if not isinstance(item, str) or not item.strip():
                    raise ValueError("ntfy_publish: tags must be a string or array of strings")
                user_tags.append(item.strip())
        elif tags is not None:
            raise ValueError("ntfy_publish: tags must be a string or array of strings")

        priority = args.get("priority")
        eff_priority = _STATUS_PRIORITY[status]
        if isinstance(priority, int):
            if not (1 <= priority <= 5):
                raise ValueError("ntfy_publish: priority int must be 1..5")
            eff_priority = str(priority)
        elif isinstance(priority, str) and priority.strip():
            p = priority.strip().lower()
            if p not in {"1", "2", "3", "4", "5", "min", "low", "default", "high", "max", "urgent"}:
                raise ValueError("ntfy_publish: priority must be 1..5 or min/low/default/high/max/urgent")
            eff_priority = p

        context_tags = [f"{k}:{_sanitize_tag(v)}" for k, v in {"repo": repo, "area": area, "branch": branch}.items() if isinstance(v, str) and v.strip()]
        default_tags = ["copilot", "computer", _STATUS_TAG[status]]
        all_tags = list(dict.fromkeys(default_tags + context_tags + user_tags))

        update = args.get("update") is not False
        eff_sequence_id: str | None = None
        if update:
            provided = args.get("sequenceId")
            if isinstance(provided, str) and provided.strip():
                eff_sequence_id = provided.strip()
            elif self._forced_sequence_id:
                eff_sequence_id = self._forced_sequence_id
            else:
                key = "|".join([session, *(v.strip() if isinstance(v, str) else "" for v in (repo, area, branch))])
                eff_sequence_id = self._sequence_ids.setdefault(key, secrets.token_urlsafe(8))

        title = args.get("title")
        title = title.strip() if isinstance(title, str) else ""
        if not title:
            title = f"{session} ({stage}/{total})" if isinstance(stage, int) and isinstance(total, int) else session

        message = args.get("message")
        message = message.strip() if isinstance(message, str) else ""
        if not message:
            parts = [
                f"Progress: {stage}/{total}" if isinstance(stage, int) and isinstance(total, int) else None,
                f"Update: {result.strip()}" if isinstance(result, str) and result.strip() else None,
                details.strip() if isinstance(details, str) and details.strip() else None,
                f"Next: {next_step.strip()}" if isinstance(next_step, str) and next_step.strip() else None,
            ]
            message = "\n".join(p for p in parts if p) or "(no message)"

        headers: dict[str, str] = {"X-Title": title, "X-Priority": eff_priority, "X-Tags": ",".join(all_tags)}
        if update and eff_sequence_id:
            headers["X-Sequence-ID"] = eff_sequence_id

        if args.get("markdown") is True:
            headers["X-Markdown"] = "yes"
        for hdr, key in (
            ("X-Click", "click"),
            ("X-Actions", "actions"),
            ("X-Icon", "icon"),
            ("X-Attach", "attach"),
            ("X-Filename", "filename"),
            ("X-Email", "email"),
        ):
            if isinstance((v := args.get(key)), str) and v.strip():
                headers[hdr] = v.strip()
        if (delay := args.get("delay")) is not None:
            headers["X-Delay"] = str(delay).strip()

        eff_cfg = cfg
        if isinstance((topic := args.get("topic")), str) and (topic := topic.strip()) and topic != cfg.topic:
            eff_cfg = NtfyConfig(
                url=cfg.url,
                topic=topic,
                token=cfg.token,
                username=cfg.username,
                password=cfg.password,
                timeout_sec=cfg.timeout_sec,
                dry_run=cfg.dry_run,
            )

        self._worker = self._worker or NtfyWorker(cfg)
        try:
            self._worker.enqueue_with_cfg(eff_cfg, headers=headers, message=message)
        except queue.Full:
            return _tool_result(
                "ntfy: queue full (dropped)",
                {"enqueued": False, "reason": "queue_full"},
                is_error=True,
            )

        return _tool_result(
            "ntfy: enqueued",
            {"enqueued": True, "queueSize": self._worker.queue_size},
        )


def _tool_result(
    text: str,
    structured: dict[str, Any] | None = None,
    *,
    is_error: bool = False,
) -> types.CallToolResult:
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=text)],
        structuredContent=structured,
        isError=is_error,
    )


def run_stdio() -> None:
    app = NtfyMcpServer()

    server = Server(
        "tiny-ntfy-mcp",
        version="0.1.0",
        instructions=(
            "When the user says ntfy_me, call ntfy_me() once, then call ntfy_publish(...) at task start, major milestones, blockers/errors, and completion. Use ntfy_off() to stop notifications. Include 'click' or 'actions' to link to relevant URLs (PRs, diffs, deployed pages, dashboards). Include 'attach' for images that add visual context (screenshots, diagrams)."
        ),
    )

    @server.list_tools()
    async def _list_tools() -> list[types.Tool]:
        return _TOOL_DEFS

    async def _handle_call_tool(req: types.CallToolRequest) -> types.ServerResult:
        name = req.params.name
        arguments = req.params.arguments or {}
        if (tool := _TOOL_BY_NAME.get(name)) is None:
            raise McpError(types.ErrorData(code=types.INVALID_PARAMS, message=f"Unknown tool: {name}"))
        try:
            jsonschema.validate(instance=arguments, schema=tool.inputSchema)
        except jsonschema.ValidationError as e:
            raise McpError(types.ErrorData(code=types.INVALID_PARAMS, message=f"Invalid params: {e.message}")) from e
        try:
            result = app.call_tool(name, arguments)
        except ValueError as e:
            raise McpError(types.ErrorData(code=types.INVALID_PARAMS, message=str(e))) from e
        return types.ServerResult(result)

    server.request_handlers[types.CallToolRequest] = _handle_call_tool

    async def _main() -> None:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    try:
        anyio.run(_main)
    finally:
        app.close()
