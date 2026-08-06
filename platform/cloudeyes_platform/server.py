"""Bounded standard-library HTTP server for CloudEyes submissions."""

from __future__ import annotations

import hmac
import json
import os
import tempfile
from collections.abc import Mapping
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .config import IngestionConfig
from .errors import IngestionError
from .ingestion import IngestionPipeline

_CHUNK_SIZE = 1024 * 1024


class TokenAuthenticator:
    """Constant-time bearer-token authentication."""

    def __init__(self, token: str | None, *, allow_anonymous: bool) -> None:
        cleaned = None if token is None else token.strip()
        if not allow_anonymous and not cleaned:
            raise ValueError("a non-empty bearer token is required")
        self.token = cleaned
        self.allow_anonymous = allow_anonymous

    def authorized(self, authorization: str | None) -> bool:
        if self.allow_anonymous:
            return True
        if authorization is None or not authorization.startswith("Bearer "):
            return False
        candidate = authorization.removeprefix("Bearer ").strip()
        return bool(candidate) and hmac.compare_digest(candidate, self.token or "")


class IngestionApplication:
    """Application state shared by request handler threads."""

    def __init__(
        self,
        config: IngestionConfig,
        *,
        token: str | None,
        allow_anonymous: bool,
    ) -> None:
        self.config = config
        self.pipeline = IngestionPipeline(config)
        self.authenticator = TokenAuthenticator(token, allow_anonymous=allow_anonymous)

    def health(self) -> dict[str, object]:
        return {
            "counts": self.pipeline.repository.counts(),
            "schema_version": "1.0.0",
            "status": "ok",
        }


def _response_bytes(value: Mapping[str, object]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def handler_class(application: IngestionApplication) -> type[BaseHTTPRequestHandler]:
    """Create a request handler bound to one application instance."""

    class CloudEyesIngestionHandler(BaseHTTPRequestHandler):
        server_version = "CloudEyesIngestion/1.0"
        sys_version = ""

        def log_message(self, format: str, *args: object) -> None:
            return

        def _send_json(self, status: int, value: Mapping[str, object]) -> None:
            content = _response_bytes(value)
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(content)
            self.wfile.flush()
            self.close_connection = True

        def _discard_request_body(self) -> None:
            """Consume a bounded fixed-length body before rejecting a request.

            Draining the body prevents Windows from resetting the connection while
            the client is still transmitting the request payload. Malformed,
            chunked, or oversized bodies are not drained.
            """

            if self.headers.get("Transfer-Encoding") is not None:
                return

            raw_length = self.headers.get("Content-Length")
            if raw_length is None:
                return

            try:
                remaining = int(raw_length)
            except ValueError:
                return

            if remaining <= 0 or remaining > application.config.max_request_bytes:
                return

            while remaining:
                chunk = self.rfile.read(min(_CHUNK_SIZE, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)

        def _error(self, error: IngestionError) -> None:
            body: dict[str, object] = {
                "error": {
                    "code": error.code,
                    "message": error.message,
                },
                "schema_version": "1.0.0",
            }
            if error.quarantine_id is not None:
                body["error"]["quarantine_id"] = error.quarantine_id  # type: ignore[index]
            self._send_json(error.status_code, body)

        def do_GET(self) -> None:  # noqa: N802
            if urlsplit(self.path).path != "/healthz":
                self._send_json(
                    HTTPStatus.NOT_FOUND,
                    {"error": {"code": "not_found", "message": "route not found"}},
                )
                return
            self._send_json(HTTPStatus.OK, application.health())

        def do_POST(self) -> None:  # noqa: N802
            if urlsplit(self.path).path != "/v1/submissions" or urlsplit(self.path).query:
                self._send_json(
                    HTTPStatus.NOT_FOUND,
                    {"error": {"code": "not_found", "message": "route not found"}},
                )
                return
            if not application.authenticator.authorized(self.headers.get("Authorization")):
                self._discard_request_body()
                self._send_json(
                    HTTPStatus.UNAUTHORIZED,
                    {
                        "error": {
                            "code": "unauthorized",
                            "message": "valid bearer authentication is required",
                        },
                        "schema_version": "1.0.0",
                    },
                )
                return
            if self.headers.get("Transfer-Encoding") is not None:
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {
                        "error": {
                            "code": "unsupported_transfer_encoding",
                            "message": "chunked request bodies are not supported",
                        },
                        "schema_version": "1.0.0",
                    },
                )
                return
            raw_length = self.headers.get("Content-Length")
            if raw_length is None:
                self._send_json(
                    HTTPStatus.LENGTH_REQUIRED,
                    {
                        "error": {
                            "code": "content_length_required",
                            "message": "Content-Length is required",
                        },
                        "schema_version": "1.0.0",
                    },
                )
                return
            try:
                content_length = int(raw_length)
            except ValueError:
                content_length = -1
            if content_length <= 0:
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {
                        "error": {
                            "code": "invalid_content_length",
                            "message": "Content-Length must be a positive integer",
                        },
                        "schema_version": "1.0.0",
                    },
                )
                return
            if content_length > application.config.max_request_bytes:
                self._send_json(
                    HTTPStatus.CONTENT_TOO_LARGE,
                    {
                        "error": {
                            "code": "request_too_large",
                            "message": (
                                f"submission exceeds {application.config.max_request_bytes} bytes"
                            ),
                        },
                        "schema_version": "1.0.0",
                    },
                )
                return

            descriptor, temporary_name = tempfile.mkstemp(
                prefix="submission-",
                suffix=".zip",
                dir=application.config.temporary_dir,
            )
            temporary = Path(temporary_name)
            try:
                remaining = content_length
                with os.fdopen(descriptor, "wb") as stream:
                    while remaining:
                        chunk = self.rfile.read(min(_CHUNK_SIZE, remaining))
                        if not chunk:
                            raise IngestionError(
                                status_code=400,
                                code="incomplete_request_body",
                                message="request body ended before Content-Length bytes were read",
                            )
                        stream.write(chunk)
                        remaining -= len(chunk)
                    stream.flush()
                    os.fsync(stream.fileno())
                headers = {key: value for key, value in self.headers.items()}
                receipt = application.pipeline.ingest(temporary, headers=headers)
                status = HTTPStatus.CREATED if receipt.status == "accepted" else HTTPStatus.OK
                self._send_json(status, receipt.to_dict())
            except IngestionError as error:
                self._error(error)
            except OSError:
                self._send_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {
                        "error": {
                            "code": "storage_failure",
                            "message": "submission could not be stored safely",
                        },
                        "schema_version": "1.0.0",
                    },
                )
            finally:
                temporary.unlink(missing_ok=True)

    return CloudEyesIngestionHandler


def create_server(
    application: IngestionApplication,
    *,
    host: str,
    port: int,
) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), handler_class(application))
    server.daemon_threads = True
    return server


__all__ = [
    "IngestionApplication",
    "TokenAuthenticator",
    "create_server",
    "handler_class",
]
