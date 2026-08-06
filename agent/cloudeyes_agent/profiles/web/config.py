"""Validated configuration for CloudEyes Web Profile v1."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from urllib.parse import SplitResult, urlsplit

from ..networking.config import NetworkScope

_KIB = 1024
_MIB = 1024 * 1024


def _validated_url(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("target_url must not be empty")
    if len(cleaned) > 2048:
        raise ValueError("target_url must not exceed 2048 characters")
    if any(character in cleaned for character in ("\r", "\n", "\x00")):
        raise ValueError("target_url must not contain control characters")

    parsed: SplitResult = urlsplit(cleaned)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("target_url must use http or https")
    if not parsed.hostname:
        raise ValueError("target_url must include a hostname")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("target_url must not include credentials")
    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError("target_url contains an invalid port") from error
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("target_url port must be between 1 and 65535")
    return cleaned


@dataclass(frozen=True, slots=True)
class WebProfileConfig:
    """Bounded HTTP GET workload for one explicitly selected web endpoint."""

    version: str = "1.0.0"
    target_url: str = "https://example.com/"
    scope: NetworkScope = NetworkScope.PUBLIC
    request_count: int = 40
    concurrency: int = 4
    warmup_requests: int = 4
    timeout_seconds: float = 10.0
    max_response_bytes: int = 2 * _MIB
    verify_tls: bool = True
    user_agent: str = "CloudEyes/0.1 web-v1"

    def __post_init__(self) -> None:
        version = self.version.strip()
        if not version:
            raise ValueError("version must not be empty")
        object.__setattr__(self, "version", version)
        object.__setattr__(self, "target_url", _validated_url(self.target_url))

        scope = self.scope if isinstance(self.scope, NetworkScope) else NetworkScope(self.scope)
        object.__setattr__(self, "scope", scope)

        for field_name, minimum, maximum in (
            ("request_count", 1, 1_000),
            ("concurrency", 1, 64),
            ("warmup_requests", 0, 100),
            ("max_response_bytes", 1 * _KIB, 16 * _MIB),
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{field_name} must be an integer")
            if not minimum <= value <= maximum:
                raise ValueError(f"{field_name} must be between {minimum} and {maximum}")

        if self.concurrency > self.request_count:
            raise ValueError("concurrency must not exceed request_count")
        if self.request_count * self.max_response_bytes > 512 * _MIB:
            raise ValueError("bounded response workload must not exceed 512 MiB")

        if isinstance(self.timeout_seconds, bool) or not isinstance(
            self.timeout_seconds, int | float
        ):
            raise TypeError("timeout_seconds must be numeric")
        timeout = float(self.timeout_seconds)
        if not 0.25 <= timeout <= 120.0:
            raise ValueError("timeout_seconds must be between 0.25 and 120")
        object.__setattr__(self, "timeout_seconds", timeout)

        if not isinstance(self.verify_tls, bool):
            raise TypeError("verify_tls must be a boolean")

        user_agent = self.user_agent.strip()
        if not user_agent or len(user_agent) > 160:
            raise ValueError("user_agent must contain between 1 and 160 characters")
        if "\r" in user_agent or "\n" in user_agent:
            raise ValueError("user_agent must not contain line breaks")
        object.__setattr__(self, "user_agent", user_agent)

    @classmethod
    def quick(
        cls,
        *,
        target_url: str = "https://example.com/",
        scope: NetworkScope = NetworkScope.PUBLIC,
        verify_tls: bool = True,
    ) -> WebProfileConfig:
        """Return a small workload suitable for CI and smoke tests."""

        return cls(
            target_url=target_url,
            scope=scope,
            request_count=6,
            concurrency=2,
            warmup_requests=1,
            timeout_seconds=5.0,
            max_response_bytes=256 * _KIB,
            verify_tls=verify_tls,
        )

    @property
    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 protocol fingerprint."""

        payload = asdict(self)
        payload["scope"] = self.scope.value
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
