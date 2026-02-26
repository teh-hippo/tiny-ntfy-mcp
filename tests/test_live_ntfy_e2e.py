from __future__ import annotations

import os
import time

import pytest

from ntfy_mcp.server import NtfyMcpServer

pytestmark = pytest.mark.live_ntfy


def test_live_publish_reaches_ntfy(monkeypatch: pytest.MonkeyPatch) -> None:
    topic = os.getenv("NTFY_CI_TOPIC")
    if not topic:
        pytest.skip("NTFY_CI_TOPIC is not set")

    url = os.getenv("NTFY_CI_URL") or "https://ntfy.sh"
    token = os.getenv("NTFY_CI_TOKEN")

    monkeypatch.setenv("NTFY_TOPIC", topic)
    monkeypatch.setenv("NTFY_URL", url)
    if token:
        monkeypatch.setenv("NTFY_TOKEN", token)
    monkeypatch.setenv("NTFY_MCP_TIMEOUT_SEC", "5")
    monkeypatch.delenv("NTFY_MCP_DRY_RUN", raising=False)
    monkeypatch.setenv("NTFY_MCP_ENABLED", "1")

    s = NtfyMcpServer()
    try:
        res = s.call_tool(
            "ntfy_publish",
            {
                "session": "ci",
                "status": "progress",
                "result": f"live-e2e {int(time.time())}",
                "update": False,
            },
        )
        assert res.structuredContent and res.structuredContent["enqueued"] is True

        worker = s._worker
        assert worker is not None
        deadline = time.time() + 15.0
        while time.time() < deadline:
            st = worker.stats
            if st.sent_ok >= 1:
                return
            if st.sent_err >= 1:
                raise AssertionError(f"ntfy publish failed: {st.last_error}")
            time.sleep(0.05)
        raise AssertionError("timed out waiting for ntfy delivery")
    finally:
        s.close()
