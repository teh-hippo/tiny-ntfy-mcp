from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time

import pytest

from ntfy_mcp.server import NtfyMcpServer


def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove all config env vars so tests start clean."""
    for key in ("NTFY_TOPIC", "NTFY_URL", "NTFY_TOKEN", "NTFY_USERNAME", "NTFY_PASSWORD", "NTFY_MCP_ENABLED", "NTFY_MCP_DRY_RUN", "NTFY_MCP_TIMEOUT_SEC", "NTFY_MCP_SEQUENCE_ID", "NTFY_MCP_LOG_LEVEL"):
        monkeypatch.delenv(key, raising=False)


def _wait_for_requests(srv, count: int, timeout: float = 2.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if len(srv.requests) >= count:
            return
        srv.event.wait(timeout=0.05)
        srv.event.clear()
    raise AssertionError(f"timed out waiting for {count} request(s), got {len(srv.requests)}")


def test_stdio_initialize_and_tools_list(monkeypatch: pytest.MonkeyPatch) -> None:
    _clean_env(monkeypatch)

    init = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "pytest", "version": "0"},
        },
    }
    initialized = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    tools_list = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}

    proc = subprocess.Popen(
        [sys.executable, "-m", "tiny_ntfy_mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=os.environ.copy(),
    )
    responses: list[dict] = []
    # Signalled by the reader once the tools/list response (id=2) is observed,
    # so the main thread waits on a real event rather than racing a join timeout.
    saw_tools_list = threading.Event()

    # Stdin is intentionally kept open until the tools/list response arrives
    # so that MCP's transport-close handler (mcp>=1.27.0) does not cancel the
    # in-flight request before it can respond.
    def _collect() -> None:
        for raw in proc.stdout:
            raw = raw.strip()
            if not raw:
                continue
            msg = json.loads(raw)
            responses.append(msg)
            if msg.get("id") == 2:
                saw_tools_list.set()
                return

    t = threading.Thread(target=_collect, daemon=True)
    t.start()
    try:
        for msg in (init, initialized, tools_list):
            proc.stdin.write(json.dumps(msg) + "\n")
            proc.stdin.flush()

        got_response = saw_tools_list.wait(timeout=5)
    finally:
        proc.stdin.close()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        # Reader exits naturally once stdout closes; join to ensure no further
        # writes to `responses` race the assertions below.
        t.join(timeout=5)

    stderr_output = proc.stderr.read()
    assert got_response, f"timed out waiting for tools/list response. Got ids: {[r.get('id') for r in responses]}\nstderr: {stderr_output}"
    assert proc.returncode == 0, stderr_output
    init_resp = next(r for r in responses if r.get("id") == 1)
    tools_resp = next(r for r in responses if r.get("id") == 2)

    assert init_resp["result"]["serverInfo"]["name"] == "tiny-ntfy-mcp"
    assert init_resp["result"]["serverInfo"]["version"]
    names = {t["name"] for t in tools_resp["result"]["tools"]}
    assert names == {"ntfy_publish", "ntfy_me", "ntfy_off"}


def test_ntfy_me_and_off_toggle_enabled_state(monkeypatch: pytest.MonkeyPatch) -> None:
    _clean_env(monkeypatch)

    s = NtfyMcpServer()
    try:
        on = s.call_tool("ntfy_me", None)
        assert on.structuredContent and on.structuredContent["enabled"] is True
        assert on.structuredContent["publishCadence"] == ["start", "milestone", "blocker_or_error", "completion"]

        off = s.call_tool("ntfy_off", None)
        assert off.structuredContent and off.structuredContent["enabled"] is False
    finally:
        s.close()


def test_publish_is_noop_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    _clean_env(monkeypatch)

    s = NtfyMcpServer()
    try:
        res = s.call_tool("ntfy_publish", {"session": "x", "result": "y"})
        assert res.structuredContent and res.structuredContent["enqueued"] is False
        assert res.structuredContent["reason"] == "disabled"
    finally:
        s.close()


def test_publish_sends_request(monkeypatch: pytest.MonkeyPatch, capture_http_server) -> None:
    base_url, http_srv = capture_http_server
    _clean_env(monkeypatch)
    monkeypatch.setenv("NTFY_TOPIC", "t1")
    monkeypatch.setenv("NTFY_URL", base_url)

    s = NtfyMcpServer()
    try:
        s.call_tool("ntfy_me", None)
        res = s.call_tool(
            "ntfy_publish",
            {"session": "build", "stage": 1, "total": 2, "status": "progress", "result": "started", "repo": "r"},
        )
        assert res.structuredContent and res.structuredContent["enqueued"] is True

        _wait_for_requests(http_srv, 1)
        req = http_srv.requests[0]
        assert req.path == "/t1"
        assert req.headers["X-Title"].startswith("build")
        assert "copilot" in req.headers["X-Tags"]
        assert "repo:r" in req.headers["X-Tags"]
        assert "Progress: 1/2" in req.body
        assert req.headers["User-Agent"].startswith("tiny-ntfy-mcp/")
    finally:
        s.close()


def test_sequence_id_reused_for_updates(monkeypatch: pytest.MonkeyPatch, capture_http_server) -> None:
    base_url, http_srv = capture_http_server
    _clean_env(monkeypatch)
    monkeypatch.setenv("NTFY_TOPIC", "t1")
    monkeypatch.setenv("NTFY_URL", base_url)

    s = NtfyMcpServer()
    try:
        s.call_tool("ntfy_me", None)
        s.call_tool("ntfy_publish", {"session": "s", "status": "progress", "repo": "r", "area": "a"})
        s.call_tool("ntfy_publish", {"session": "s", "status": "progress", "repo": "r", "area": "a"})

        _wait_for_requests(http_srv, 2)
        h1 = {k.lower(): v for k, v in http_srv.requests[0].headers.items()}
        h2 = {k.lower(): v for k, v in http_srv.requests[1].headers.items()}
        sid1 = h1.get("x-sequence-id")
        sid2 = h2.get("x-sequence-id")
        assert sid1 and sid1 == sid2
    finally:
        s.close()


def test_unicode_title_is_rfc2047_encoded(monkeypatch: pytest.MonkeyPatch, capture_http_server) -> None:
    base_url, http_srv = capture_http_server
    _clean_env(monkeypatch)
    monkeypatch.setenv("NTFY_TOPIC", "t1")
    monkeypatch.setenv("NTFY_URL", base_url)
    monkeypatch.setenv("NTFY_MCP_ENABLED", "1")

    s = NtfyMcpServer()
    try:
        s.call_tool("ntfy_publish", {"session": "s", "title": "Hello — world", "message": "x"})
        _wait_for_requests(http_srv, 1)
        title = http_srv.requests[0].headers["X-Title"]
        assert title.isascii()
        assert "=?utf-8?" in title.lower()
    finally:
        s.close()


def test_topic_override(monkeypatch: pytest.MonkeyPatch, capture_http_server) -> None:
    base_url, http_srv = capture_http_server
    _clean_env(monkeypatch)
    monkeypatch.setenv("NTFY_TOPIC", "t1")
    monkeypatch.setenv("NTFY_URL", base_url)
    monkeypatch.setenv("NTFY_MCP_ENABLED", "1")

    s = NtfyMcpServer()
    try:
        s.call_tool("ntfy_publish", {"session": "s", "message": "x", "topic": "t2"})
        _wait_for_requests(http_srv, 1)
        assert http_srv.requests[0].path == "/t2"
    finally:
        s.close()


def test_version_fallback_when_package_not_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib

    import ntfy_mcp._version as vmod

    def _raise(*_args, **_kwargs):
        raise importlib.metadata.PackageNotFoundError("fake")

    monkeypatch.setattr(importlib.metadata, "version", _raise)
    # Re-execute the module body with the patched function.
    importlib.reload(vmod)
    try:
        assert vmod.__version__ == "0.0.0+dev"
    finally:
        importlib.reload(vmod)
