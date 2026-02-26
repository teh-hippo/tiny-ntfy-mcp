from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from ntfy_mcp.server import NtfyMcpServer


def _tmp_paths(tmp_path: Path) -> tuple[Path, Path, Path]:
    state = tmp_path / "state.json"
    cfg = tmp_path / "config.json"
    env = tmp_path / ".env"
    return state, cfg, env


def _wait_for_requests(srv, count: int, timeout: float = 2.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if len(srv.requests) >= count:
            return
        srv.event.wait(timeout=0.05)
        srv.event.clear()
    raise AssertionError(f"timed out waiting for {count} request(s), got {len(srv.requests)}")


def test_stdio_initialize_and_tools_list(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state, cfg, env = _tmp_paths(tmp_path)
    state.write_text(json.dumps({"enabled": False}), encoding="utf-8")
    cfg.write_text("{}", encoding="utf-8")
    env.write_text("", encoding="utf-8")

    monkeypatch.setenv("NTFY_MCP_STATE_PATH", str(state))
    monkeypatch.setenv("NTFY_MCP_CONFIG_PATH", str(cfg))
    monkeypatch.setenv("NTFY_MCP_ENV_PATH", str(env))
    monkeypatch.delenv("NTFY_MCP_ENABLED", raising=False)

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
    input_text = "\n".join(json.dumps(m) for m in (init, initialized, tools_list)) + "\n"

    proc = subprocess.run(
        [sys.executable, "-m", "tiny_ntfy_mcp"],
        input=input_text,
        text=True,
        capture_output=True,
        env=os.environ.copy(),
        timeout=5,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr

    responses = [json.loads(line) for line in proc.stdout.splitlines()]
    init_resp = next(r for r in responses if r.get("id") == 1)
    tools_resp = next(r for r in responses if r.get("id") == 2)

    assert init_resp["result"]["serverInfo"]["name"] == "tiny-ntfy-mcp"
    names = {t["name"] for t in tools_resp["result"]["tools"]}
    assert names == {"ntfy_publish", "ntfy_me", "ntfy_off"}


def test_ntfy_me_and_off_toggle_enabled_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state, cfg, env = _tmp_paths(tmp_path)
    state.write_text(json.dumps({"enabled": False}), encoding="utf-8")
    cfg.write_text("{}", encoding="utf-8")
    env.write_text("", encoding="utf-8")

    monkeypatch.setenv("NTFY_MCP_STATE_PATH", str(state))
    monkeypatch.setenv("NTFY_MCP_CONFIG_PATH", str(cfg))
    monkeypatch.setenv("NTFY_MCP_ENV_PATH", str(env))
    monkeypatch.delenv("NTFY_MCP_ENABLED", raising=False)

    s = NtfyMcpServer()
    try:
        on = s.call_tool("ntfy_me", None)
        assert on.structuredContent and on.structuredContent["enabled"] is True
        assert on.structuredContent["publishCadence"] == ["start", "milestone", "blocker_or_error", "completion"]
        assert json.loads(state.read_text(encoding="utf-8"))["enabled"] is True

        off = s.call_tool("ntfy_off", None)
        assert off.structuredContent and off.structuredContent["enabled"] is False
        assert json.loads(state.read_text(encoding="utf-8"))["enabled"] is False
    finally:
        s.close()


def test_publish_is_noop_when_disabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state, cfg, env = _tmp_paths(tmp_path)
    state.write_text(json.dumps({"enabled": False}), encoding="utf-8")
    cfg.write_text("{}", encoding="utf-8")
    env.write_text("", encoding="utf-8")

    monkeypatch.setenv("NTFY_MCP_STATE_PATH", str(state))
    monkeypatch.setenv("NTFY_MCP_CONFIG_PATH", str(cfg))
    monkeypatch.setenv("NTFY_MCP_ENV_PATH", str(env))
    monkeypatch.delenv("NTFY_MCP_ENABLED", raising=False)

    s = NtfyMcpServer()
    try:
        res = s.call_tool("ntfy_publish", {"session": "x", "result": "y"})
        assert res.structuredContent and res.structuredContent["enqueued"] is False
        assert res.structuredContent["reason"] == "disabled"
    finally:
        s.close()


def test_publish_sends_request(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capture_http_server) -> None:
    base_url, http_srv = capture_http_server
    state, cfg, env = _tmp_paths(tmp_path)
    state.write_text(json.dumps({"enabled": True}), encoding="utf-8")
    cfg.write_text(json.dumps({"NTFY_TOPIC": "t1", "NTFY_URL": base_url}), encoding="utf-8")
    env.write_text("", encoding="utf-8")

    monkeypatch.setenv("NTFY_MCP_STATE_PATH", str(state))
    monkeypatch.setenv("NTFY_MCP_CONFIG_PATH", str(cfg))
    monkeypatch.setenv("NTFY_MCP_ENV_PATH", str(env))
    monkeypatch.delenv("NTFY_MCP_ENABLED", raising=False)

    s = NtfyMcpServer()
    try:
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
    finally:
        s.close()


def test_sequence_id_reused_for_updates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capture_http_server) -> None:
    base_url, http_srv = capture_http_server
    state, cfg, env = _tmp_paths(tmp_path)
    state.write_text(json.dumps({"enabled": True}), encoding="utf-8")
    cfg.write_text(json.dumps({"NTFY_TOPIC": "t1", "NTFY_URL": base_url}), encoding="utf-8")
    env.write_text("", encoding="utf-8")

    monkeypatch.setenv("NTFY_MCP_STATE_PATH", str(state))
    monkeypatch.setenv("NTFY_MCP_CONFIG_PATH", str(cfg))
    monkeypatch.setenv("NTFY_MCP_ENV_PATH", str(env))
    monkeypatch.delenv("NTFY_MCP_ENABLED", raising=False)

    s = NtfyMcpServer()
    try:
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


def test_unicode_title_is_rfc2047_encoded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capture_http_server) -> None:
    base_url, http_srv = capture_http_server
    state, cfg, env = _tmp_paths(tmp_path)
    state.write_text(json.dumps({"enabled": True}), encoding="utf-8")
    cfg.write_text(json.dumps({"NTFY_TOPIC": "t1", "NTFY_URL": base_url}), encoding="utf-8")
    env.write_text("", encoding="utf-8")

    monkeypatch.setenv("NTFY_MCP_STATE_PATH", str(state))
    monkeypatch.setenv("NTFY_MCP_CONFIG_PATH", str(cfg))
    monkeypatch.setenv("NTFY_MCP_ENV_PATH", str(env))
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


def test_topic_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capture_http_server) -> None:
    base_url, http_srv = capture_http_server
    state, cfg, env = _tmp_paths(tmp_path)
    state.write_text(json.dumps({"enabled": True}), encoding="utf-8")
    cfg.write_text(json.dumps({"NTFY_TOPIC": "t1", "NTFY_URL": base_url}), encoding="utf-8")
    env.write_text("", encoding="utf-8")

    monkeypatch.setenv("NTFY_MCP_STATE_PATH", str(state))
    monkeypatch.setenv("NTFY_MCP_CONFIG_PATH", str(cfg))
    monkeypatch.setenv("NTFY_MCP_ENV_PATH", str(env))
    monkeypatch.setenv("NTFY_MCP_ENABLED", "1")

    s = NtfyMcpServer()
    try:
        s.call_tool("ntfy_publish", {"session": "s", "message": "x", "topic": "t2"})
        _wait_for_requests(http_srv, 1)
        assert http_srv.requests[0].path == "/t2"
    finally:
        s.close()
