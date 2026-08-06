"""Local HTTP endpoint used by networking profile tests."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

_PAYLOAD = bytes(range(256)) * 1024


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        if self.path.split("?", 1)[0] != "/download":
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(_PAYLOAD)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(_PAYLOAD)

    def do_POST(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        if self.path.split("?", 1)[0] != "/upload":
            self.send_error(404)
            return
        content_length = int(self.headers.get("Content-Length", "0"))
        remaining = content_length
        while remaining:
            chunk = self.rfile.read(min(64 * 1024, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.send_header("Connection", "close")
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        return


@contextmanager
def local_network_endpoint() -> Iterator[tuple[str, str]]:
    """Run a loopback HTTP endpoint and yield download and upload URLs."""

    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        yield f"http://{host}:{port}/download", f"http://{host}:{port}/upload"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2.0)
