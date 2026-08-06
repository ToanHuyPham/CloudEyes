"""Explicit, bounded HTTP submission for verified CloudEyes result bundles."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import socket
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from .. import __version__
from .model import SubmissionReceipt
from .verification import verify_bundle

MAX_RESPONSE_BYTES = 64 * 1024
DEFAULT_TIMEOUT_SECONDS = 30.0


class SubmissionError(RuntimeError):
    """Raised when a verified bundle cannot be submitted safely."""


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def _is_private_http_host(hostname: str, port: int | None) -> bool:
    if hostname.casefold() == "localhost":
        return True
    try:
        addresses = {ipaddress.ip_address(hostname)}
    except ValueError:
        try:
            resolved = socket.getaddrinfo(hostname, port or 80, type=socket.SOCK_STREAM)
        except OSError as error:
            raise SubmissionError(f"cannot resolve submission endpoint: {error}") from error
        addresses = {ipaddress.ip_address(item[4][0]) for item in resolved}
    return bool(addresses) and all(
        address.is_private or address.is_loopback or address.is_link_local for address in addresses
    )


def validate_endpoint(endpoint: str, *, allow_http: bool) -> str:
    """Return a normalized safe endpoint or raise ``SubmissionError``."""

    try:
        parsed = urlsplit(endpoint)
        port = parsed.port
    except ValueError as error:
        raise SubmissionError(f"invalid submission endpoint: {error}") from error
    if parsed.scheme not in {"https", "http"}:
        raise SubmissionError("submission endpoint must use HTTPS")
    if not parsed.hostname:
        raise SubmissionError("submission endpoint must contain a hostname")
    if parsed.username is not None or parsed.password is not None:
        raise SubmissionError("submission endpoint must not contain credentials")
    if parsed.query or parsed.fragment:
        raise SubmissionError("submission endpoint must not contain query or fragment data")
    if parsed.scheme == "http":
        if not allow_http:
            raise SubmissionError("plain HTTP submission requires --allow-http")
        if not _is_private_http_host(parsed.hostname, port):
            raise SubmissionError("plain HTTP is restricted to private or loopback endpoints")
    hostname = parsed.hostname
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    netloc = f"{hostname}:{port}" if port is not None else hostname
    return urlunsplit((parsed.scheme, netloc, parsed.path or "/", "", ""))


def _bounded_response(stream) -> bytes:  # noqa: ANN001
    content = stream.read(MAX_RESPONSE_BYTES + 1)
    if len(content) > MAX_RESPONSE_BYTES:
        raise SubmissionError("submission response exceeds the safety limit")
    return content


def _remote_submission_id(content: bytes) -> str | None:
    if not content:
        return None
    try:
        value = json.loads(content.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict):
        return None
    submission_id = value.get("submission_id")
    if not isinstance(submission_id, str):
        return None
    cleaned = submission_id.strip()
    return cleaned[:256] or None


def submission_plan(
    bundle: Path,
    *,
    endpoint: str,
    allow_http: bool,
    authenticated: bool,
) -> dict[str, object]:
    """Verify a bundle and return a network-free submission plan."""

    verification = verify_bundle(bundle)
    normalized_endpoint = validate_endpoint(endpoint, allow_http=allow_http)
    return {
        "authenticated": authenticated,
        "bundle_id": verification.bundle_id,
        "bundle_sha256": verification.bundle_sha256,
        "endpoint": normalized_endpoint,
        "file_count": verification.file_count,
        "mode": "dry_run",
        "sample_count": verification.sample_count,
        "warnings": list(verification.warnings),
    }


def submit_bundle(
    bundle: Path,
    *,
    endpoint: str,
    token: str | None,
    allow_http: bool = False,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    submitted_at: datetime | None = None,
) -> SubmissionReceipt:
    """Verify and POST one bundle without redirects or unbounded responses."""

    if timeout_seconds <= 0 or timeout_seconds > 300:
        raise SubmissionError("submission timeout must be between 0 and 300 seconds")
    verification = verify_bundle(bundle)
    normalized_endpoint = validate_endpoint(endpoint, allow_http=allow_http)
    content = bundle.expanduser().read_bytes()
    headers = {
        "Content-Type": "application/vnd.cloudeyes.bundle+zip; version=1",
        "Idempotency-Key": verification.bundle_sha256,
        "User-Agent": f"CloudEyes/{__version__}",
        "X-CloudEyes-Bundle-Id": verification.bundle_id,
        "X-CloudEyes-Bundle-SHA256": verification.bundle_sha256,
    }
    if token is not None:
        cleaned_token = token.strip()
        if not cleaned_token:
            raise SubmissionError("submission token must not be empty")
        headers["Authorization"] = f"Bearer {cleaned_token}"

    request = urllib.request.Request(
        normalized_endpoint,
        data=content,
        headers=headers,
        method="POST",
    )
    opener = urllib.request.build_opener(_NoRedirectHandler())
    status_code: int
    response_content: bytes
    try:
        with opener.open(request, timeout=timeout_seconds) as response:
            status_code = response.status
            response_content = _bounded_response(response)
    except urllib.error.HTTPError as error:
        status_code = error.code
        response_content = _bounded_response(error)
    except OSError as error:
        raise SubmissionError(f"submission request failed: {error}") from error

    timestamp = submitted_at or datetime.now(UTC)
    if timestamp.tzinfo is None:
        raise SubmissionError("submitted_at must contain timezone information")
    return SubmissionReceipt(
        schema_version="1.0.0",
        submitted_at=timestamp,
        endpoint=normalized_endpoint,
        bundle_id=verification.bundle_id,
        bundle_sha256=verification.bundle_sha256,
        status_code=status_code,
        accepted=200 <= status_code < 300,
        remote_submission_id=_remote_submission_id(response_content),
        response_sha256=hashlib.sha256(response_content).hexdigest(),
    )


def token_from_environment(name: str) -> str | None:
    """Read a bearer token without exposing it as a command-line argument."""

    if not name or not name.replace("_", "A").isalnum() or name[0].isdigit():
        raise SubmissionError("token environment variable name is invalid")
    return os.environ.get(name)


__all__ = [
    "DEFAULT_TIMEOUT_SECONDS",
    "SubmissionError",
    "submission_plan",
    "submit_bundle",
    "token_from_environment",
    "validate_endpoint",
]
