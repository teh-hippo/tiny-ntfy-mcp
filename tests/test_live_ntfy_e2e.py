from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from ntfy_mcp.server import NtfyMcpServer

pytestmark = pytest.mark.live_ntfy


def _tmp_paths(tmp_path: Path) -> tuple[Path, Path, Path]:
    state = tmp_path / "state.json"
    cfg = tmp_path / "config.json"
    env = tmp_path / ".env"
    return state, cfg, env


def test_live_publish_reaches_ntfy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    topic = os.getenv("NTFY_CI_TOPIC")
    if not topic:
        pytest.skip("NTFY_CI_TOPIC is not set")

    url = os.getenv("NTFY_CI_URL") or "https://ntfy.sh"
    token = os.getenv("NTFY_CI_TOKEN")

    state, cfg, env = _tmp_paths(tmp_path)
    state.write_text(json.dumps({"enabled": True}), encoding="utf-8")
    cfg_payload = {"NTFY_TOPIC": topic, "NTFY_URL": url}
    if token:
        cfg_payload["NTFY_TOKEN"] = token
    cfg.write_text(json.dumps(cfg_payload), encoding="utf-8")
    env.write_text("", encoding="utf-8")

    monkeypatch.setenv("NTFY_MCP_STATE_PATH", str(state))
    monkeypatch.setenv("NTFY_MCP_CONFIG_PATH", str(cfg))
    monkeypatch.setenv("NTFY_MCP_ENV_PATH", str(env))
    monkeypatch.setenv("NTFY_MCP_TIMEOUT_SEC", "5")
    monkeypatch.delenv("NTFY_MCP_DRY_RUN", raising=False)
    monkeypatch.delenv("NTFY_MCP_ENABLED", raising=False)

    s = NtfyMcpServer()
    try:
        res = s.call_tool(
            "ntfy.publish",
            {
                "session": "ci",
                "status": "progress",
                "result": f"live-e2e {int(time.time())}",
                "update": False,
            },
        )
        assert res.structuredContent and res.structuredContent["enqueued"] is True

        deadline = time.time() + 15.0
        while time.time() < deadline:
            st = s.call_tool("ntfy.status", None).structuredContent or {}
            if (st.get("sentOk") or 0) >= 1:
                return
            if (st.get("sentErr") or 0) >= 1:
                raise AssertionError(f"ntfy publish failed: {st.get('lastError')}")
            time.sleep(0.05)
        raise AssertionError("timed out waiting for ntfy delivery")
    finally:
        s.close()
