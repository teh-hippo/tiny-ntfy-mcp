from __future__ import annotations

import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest


@dataclass
class CapturedRequest:
    path: str
    headers: dict[str, str]
    body: str


class _CaptureHandler(BaseHTTPRequestHandler):
    server: _CaptureServer  # type: ignore[assignment]

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        # Silence noisy test output.
        return

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length).decode("utf-8", errors="replace")
        captured = CapturedRequest(
            path=self.path,
            headers={k: v for k, v in self.headers.items()},
            body=body,
        )
        self.server.requests.append(captured)
        self.server.event.set()

        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"ok")


class _CaptureServer(ThreadingHTTPServer):
    def __init__(self, host: str = "127.0.0.1") -> None:
        super().__init__((host, 0), _CaptureHandler)
        self.requests: list[CapturedRequest] = []
        self.event = threading.Event()


@pytest.fixture()
def capture_http_server() -> tuple[str, _CaptureServer]:
    server = _CaptureServer()
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        yield base_url, server
    finally:
        server.shutdown()
        server.server_close()
