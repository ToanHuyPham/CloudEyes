"""Local HTTP endpoint used by Web Profile tests."""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

_PAYLOAD = (b"CloudEyes web profile test payload\n" * 2048)[: 64 * 1024]
_LARGE_PAYLOAD = bytes(range(256)) * 8192


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    _counter = 0
    _counter_lock = threading.Lock()

    @classmethod
    def _next_count(cls) -> int:
        with cls._counter_lock:
            cls._counter += 1
            return cls._counter

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        path = self.path.split("?", 1)[0]
        count = self._next_count()
        if path == "/slow":
            time.sleep(0.02)
            self._send(200, _PAYLOAD)
            return
        if path == "/flaky":
            if count % 3 == 0:
                self._send(503, b"temporary failure")
            else:
                self._send(200, _PAYLOAD)
            return
        if path == "/error":
            self._send(503, b"service unavailable")
            return
        if path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/ok")
            self.send_header("Content-Length", "0")
            self.send_header("Connection", "close")
            self.end_headers()
            return
        if path == "/empty":
            self._send(204, b"")
            return
        if path == "/large":
            self._send(200, _LARGE_PAYLOAD)
            return
        if path == "/ok":
            self._send(200, _PAYLOAD)
            return
        self.send_error(404)

    def _send(self, status: int, payload: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return


@contextmanager
def local_web_endpoint() -> Iterator[str]:
    """Run a loopback web endpoint and yield its base URL."""

    _Handler._counter = 0
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2.0)
