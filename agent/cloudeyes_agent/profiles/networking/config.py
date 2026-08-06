"""Validated configuration for the CloudEyes Networking Profile v1."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from urllib.parse import SplitResult, urlsplit

_KIB = 1024
_MIB = 1024 * 1024


class NetworkScope(StrEnum):
    """Address scope allowed for a networking benchmark target."""

    PUBLIC = "public"
    PRIVATE = "private"


def _validated_url(value: str, *, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be empty")
    if len(cleaned) > 2048:
        raise ValueError(f"{field_name} must not exceed 2048 characters")
    if any(character in cleaned for character in ("\r", "\n", "\x00")):
        raise ValueError(f"{field_name} must not contain control characters")

    parsed: SplitResult = urlsplit(cleaned)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"{field_name} must use http or https")
    if not parsed.hostname:
        raise ValueError(f"{field_name} must include a hostname")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError(f"{field_name} must not include credentials")
    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError(f"{field_name} contains an invalid port") from error
    if port is not None and not 1 <= port <= 65535:
        raise ValueError(f"{field_name} port must be between 1 and 65535")
    return cleaned


@dataclass(frozen=True, slots=True)
class NetworkingProfileConfig:
    """Bounded and privacy-safe endpoint benchmark configuration."""

    version: str = "1.0.0"
    target_url: str = "https://example.com/"
    upload_url: str | None = None
    scope: NetworkScope = NetworkScope.PUBLIC
    repetitions: int = 5
    timeout_seconds: float = 10.0
    download_limit_bytes: int = 4 * _MIB
    upload_bytes: int = 1 * _MIB
    ping_count: int = 5
    verify_tls: bool = True
    user_agent: str = "CloudEyes/0.1 networking-v1"

    def __post_init__(self) -> None:
        version = self.version.strip()
        if not version:
            raise ValueError("version must not be empty")
        object.__setattr__(self, "version", version)

        object.__setattr__(
            self,
            "target_url",
            _validated_url(self.target_url, field_name="target_url"),
        )
        if self.upload_url is not None:
            object.__setattr__(
                self,
                "upload_url",
                _validated_url(self.upload_url, field_name="upload_url"),
            )

        scope = self.scope if isinstance(self.scope, NetworkScope) else NetworkScope(self.scope)
        object.__setattr__(self, "scope", scope)

        for field_name, minimum, maximum in (
            ("repetitions", 1, 20),
            ("download_limit_bytes", 1 * _KIB, 64 * _MIB),
            ("upload_bytes", 1 * _KIB, 16 * _MIB),
            ("ping_count", 0, 20),
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{field_name} must be an integer")
            if not minimum <= value <= maximum:
                raise ValueError(f"{field_name} must be between {minimum} and {maximum}")

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
        upload_url: str | None = None,
        scope: NetworkScope = NetworkScope.PUBLIC,
        verify_tls: bool = True,
    ) -> NetworkingProfileConfig:
        """Return a small workload suitable for smoke tests and CI."""

        return cls(
            target_url=target_url,
            upload_url=upload_url,
            scope=scope,
            repetitions=2,
            timeout_seconds=5.0,
            download_limit_bytes=256 * _KIB,
            upload_bytes=64 * _KIB,
            ping_count=2,
            verify_tls=verify_tls,
        )

    @property
    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 protocol fingerprint."""

        payload = asdict(self)
        payload["scope"] = self.scope.value
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
