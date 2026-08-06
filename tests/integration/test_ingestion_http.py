"""End-to-end HTTP ingestion tests using the built-in loopback server."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager

from cloudeyes_platform.config import IngestionConfig
from cloudeyes_platform.server import IngestionApplication, create_server

from tests.platform_factory import build_test_bundle


@contextmanager
def running_server(tmp_path) -> Iterator[str]:
    application = IngestionApplication(
        IngestionConfig(tmp_path / "service"),
        token="test-token",
        allow_anonymous=False,
    )
    server = create_server(application, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    try:
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _submit(url: str, content: bytes, headers: dict[str, str]) -> tuple[int, dict[str, object]]:
    request = urllib.request.Request(
        f"{url}/v1/submissions",
        data=content,
        headers={**headers, "Authorization": "Bearer test-token"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


def test_http_accepts_and_deduplicates_verified_bundle(tmp_path) -> None:
    bundle, headers = build_test_bundle(tmp_path)
    with running_server(tmp_path) as url:
        first_status, first = _submit(url, bundle.read_bytes(), headers)
        second_status, second = _submit(url, bundle.read_bytes(), headers)
        with urllib.request.urlopen(f"{url}/healthz", timeout=5) as response:
            health = json.loads(response.read().decode("utf-8"))

    assert first_status == 201
    assert first["status"] == "accepted"
    assert second_status == 200
    assert second["status"] == "duplicate"
    assert second["duplicate_of"] == first["submission_id"]
    assert health["counts"]["submissions"] == 1
    assert health["counts"]["samples"] == 1


def test_http_rejects_missing_authentication_before_ingestion(tmp_path) -> None:
    bundle, headers = build_test_bundle(tmp_path)
    with running_server(tmp_path) as url:
        request = urllib.request.Request(
            f"{url}/v1/submissions",
            data=bundle.read_bytes(),
            headers=headers,
            method="POST",
        )
        try:
            urllib.request.urlopen(request, timeout=5)
        except urllib.error.HTTPError as error:
            body = json.loads(error.read().decode("utf-8"))
            status = error.code
        else:
            raise AssertionError("unauthenticated request unexpectedly succeeded")

    assert status == 401
    assert body["error"]["code"] == "unauthorized"
