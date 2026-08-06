"""Validated configuration for CloudEyes Compute Profile v1."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

_MIB = 1024 * 1024


@dataclass(frozen=True, slots=True)
class ComputeProfileConfig:
    """Bounded, portable CPU workloads implemented with the Python standard library."""

    version: str = "1.0.0"
    repetitions: int = 3
    warmup_iterations: int = 5_000
    integer_iterations: int = 350_000
    floating_point_iterations: int = 300_000
    sha256_block_bytes: int = 1 * _MIB
    sha256_iterations: int = 64
    compression_block_bytes: int = 1 * _MIB
    compression_iterations: int = 16
    compression_level: int = 6
    workers: int = 0
    max_auto_workers: int = 4
    worker_timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        version = self.version.strip()
        if not version:
            raise ValueError("version must not be empty")
        object.__setattr__(self, "version", version)

        integer_limits = {
            "repetitions": (1, 9),
            "warmup_iterations": (1, 1_000_000),
            "integer_iterations": (1, 10_000_000),
            "floating_point_iterations": (1, 10_000_000),
            "sha256_block_bytes": (1, 16 * _MIB),
            "sha256_iterations": (1, 4_096),
            "compression_block_bytes": (1, 16 * _MIB),
            "compression_iterations": (1, 1_024),
            "compression_level": (0, 9),
            "workers": (0, 64),
            "max_auto_workers": (1, 64),
        }
        for field_name, (minimum, maximum) in integer_limits.items():
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{field_name} must be an integer")
            if not minimum <= value <= maximum:
                raise ValueError(f"{field_name} must be between {minimum} and {maximum}")

        timeout = self.worker_timeout_seconds
        if isinstance(timeout, bool) or not isinstance(timeout, int | float):
            raise TypeError("worker_timeout_seconds must be numeric")
        timeout = float(timeout)
        if not 1.0 <= timeout <= 600.0:
            raise ValueError("worker_timeout_seconds must be between 1 and 600")
        object.__setattr__(self, "worker_timeout_seconds", timeout)

        sha256_bytes = self.sha256_block_bytes * self.sha256_iterations
        if sha256_bytes > 4 * 1024 * _MIB:
            raise ValueError("SHA-256 workload must not exceed 4 GiB per repetition")

        compression_bytes = self.compression_block_bytes * self.compression_iterations
        if compression_bytes > 2 * 1024 * _MIB:
            raise ValueError("compression workload must not exceed 2 GiB per repetition")

    @classmethod
    def quick(cls, *, workers: int = 0) -> ComputeProfileConfig:
        """Return a small configuration for CI and smoke tests."""

        return cls(
            repetitions=2,
            warmup_iterations=500,
            integer_iterations=25_000,
            floating_point_iterations=20_000,
            sha256_block_bytes=256 * 1024,
            sha256_iterations=4,
            compression_block_bytes=256 * 1024,
            compression_iterations=2,
            workers=workers,
            max_auto_workers=2,
            worker_timeout_seconds=30.0,
        )

    @property
    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 protocol fingerprint."""

        payload = json.dumps(
            asdict(self),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
