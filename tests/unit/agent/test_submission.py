"""Tests for explicit bounded result-bundle submission."""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from cloudeyes_agent.bundle import (
    SubmissionError,
    build_bundle,
    submission_plan,
    submit_bundle,
    validate_endpoint,
)
from cloudeyes_core.serialization import dump

from tests.core_factory import make_sample


def _bundle(tmp_path: Path) -> Path:
    sample = tmp_path / "sample.json"
    dump(make_sample(), sample)
    bundle = tmp_path / "bundle.zip"
    build_bundle(
        (sample,),
        output=bundle,
        created_at=datetime(2026, 8, 6, tzinfo=UTC),
    )
    return bundle


def test_dry_run_plan_does_not_contact_network(tmp_path: Path) -> None:
    plan = submission_plan(
        _bundle(tmp_path),
        endpoint="https://collector.example.test/v1/submissions",
        allow_http=False,
        authenticated=False,
    )

    assert plan["mode"] == "dry_run"
    assert plan["sample_count"] == 1
    assert plan["authenticated"] is False


def test_plain_http_requires_explicit_private_endpoint_policy() -> None:
    with pytest.raises(SubmissionError, match="requires --allow-http"):
        validate_endpoint("http://127.0.0.1:8080/submit", allow_http=False)

    assert (
        validate_endpoint("http://127.0.0.1:8080/submit", allow_http=True)
        == "http://127.0.0.1:8080/submit"
    )

    with pytest.raises(SubmissionError, match="private or loopback"):
        validate_endpoint("http://8.8.8.8/submit", allow_http=True)


def test_endpoint_rejects_credentials_query_and_fragment() -> None:
    with pytest.raises(SubmissionError, match="credentials"):
        validate_endpoint("https://user:pass@example.test/submit", allow_http=False)
    with pytest.raises(SubmissionError, match="query or fragment"):
        validate_endpoint("https://example.test/submit?token=x", allow_http=False)


def test_submit_posts_verified_bundle_and_returns_safe_receipt(tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers["Content-Length"])
            captured["body"] = self.rfile.read(length)
            captured["authorization"] = self.headers.get("Authorization")
            captured["idempotency"] = self.headers.get("Idempotency-Key")
            captured["bundle_sha256"] = self.headers.get("X-CloudEyes-Bundle-SHA256")
            response = json.dumps({"submission_id": "submission-123"}).encode()
            self.send_response(202)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        bundle = _bundle(tmp_path)
        receipt = submit_bundle(
            bundle,
            endpoint=f"http://127.0.0.1:{server.server_port}/v1/submissions",
            token="top-secret-token",
            allow_http=True,
            submitted_at=datetime(2026, 8, 6, 12, tzinfo=UTC),
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert receipt.accepted is True
    assert receipt.status_code == 202
    assert receipt.remote_submission_id == "submission-123"
    assert receipt.endpoint.endswith("/v1/submissions")
    assert captured["authorization"] == "Bearer top-secret-token"
    assert captured["idempotency"] == receipt.bundle_sha256
    assert captured["bundle_sha256"] == receipt.bundle_sha256
    assert captured["body"] == bundle.read_bytes()
    assert "top-secret-token" not in str(receipt)


def test_non_success_response_produces_rejected_receipt(tmp_path: Path) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers["Content-Length"])
            self.rfile.read(length)
            self.send_response(409)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        receipt = submit_bundle(
            _bundle(tmp_path),
            endpoint=f"http://127.0.0.1:{server.server_port}/submit",
            token=None,
            allow_http=True,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert receipt.accepted is False
    assert receipt.status_code == 409
