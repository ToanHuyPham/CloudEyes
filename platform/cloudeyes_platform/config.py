"""Configuration and local filesystem layout for Backend Ingestion v1."""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from pathlib import Path

from .errors import ConfigurationError

MAX_REQUEST_BYTES = 128 * 1024 * 1024
DEFAULT_DATA_DIR = Path("data/platform")


def _is_loopback_host(host: str) -> bool:
    if host.casefold() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


@dataclass(frozen=True, slots=True)
class IngestionConfig:
    """Resolved ingestion service configuration."""

    data_dir: Path
    max_request_bytes: int = MAX_REQUEST_BYTES
    quarantine_payloads: bool = False

    def __post_init__(self) -> None:
        resolved = self.data_dir.expanduser().resolve()
        if self.max_request_bytes <= 0 or self.max_request_bytes > MAX_REQUEST_BYTES:
            raise ConfigurationError(f"max_request_bytes must be between 1 and {MAX_REQUEST_BYTES}")
        object.__setattr__(self, "data_dir", resolved)

    @property
    def database_path(self) -> Path:
        return self.data_dir / "ingestion.sqlite3"

    @property
    def bundle_dir(self) -> Path:
        return self.data_dir / "bundles"

    @property
    def quarantine_dir(self) -> Path:
        return self.data_dir / "quarantine"

    @property
    def temporary_dir(self) -> Path:
        return self.data_dir / "tmp"

    def prepare(self) -> None:
        """Create private service directories."""

        for path in (
            self.data_dir,
            self.bundle_dir,
            self.quarantine_dir,
            self.temporary_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)
            try:
                path.chmod(0o700)
            except OSError:
                pass


def validate_bind_policy(
    host: str,
    *,
    allow_anonymous: bool,
    allow_insecure_network: bool,
) -> None:
    """Reject unsafe built-in HTTP server exposure by default."""

    loopback = _is_loopback_host(host)
    if allow_anonymous and not loopback:
        raise ConfigurationError("anonymous ingestion is restricted to loopback binds")
    if not loopback and not allow_insecure_network:
        raise ConfigurationError(
            "non-loopback HTTP binding requires --allow-insecure-network; "
            "production deployments should use a TLS reverse proxy"
        )


__all__ = [
    "DEFAULT_DATA_DIR",
    "MAX_REQUEST_BYTES",
    "IngestionConfig",
    "validate_bind_policy",
]
