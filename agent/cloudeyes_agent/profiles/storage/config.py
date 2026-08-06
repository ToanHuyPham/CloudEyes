"""Validated configuration for the CloudEyes Storage Profile v1."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

_KIB = 1024
_MIB = 1024 * 1024
_GIB = 1024 * _MIB


@dataclass(frozen=True, slots=True)
class StorageProfileConfig:
    """Bounded and reproducible local storage workload configuration."""

    version: str = "1.0.0"
    file_size_bytes: int = 64 * _MIB
    sequential_block_bytes: int = 1 * _MIB
    random_block_bytes: int = 4 * _KIB
    random_operations: int = 2048
    fsync_operations: int = 16
    repetitions: int = 3
    warmup_operations: int = 16
    fsync_writes: bool = True
    random_seed: int = 20260806

    def __post_init__(self) -> None:
        version = self.version.strip()
        if not version:
            raise ValueError("version must not be empty")
        object.__setattr__(self, "version", version)

        if not isinstance(self.fsync_writes, bool):
            raise TypeError("fsync_writes must be a boolean")

        integer_limits = {
            "file_size_bytes": (1 * _MIB, 1 * _GIB),
            "sequential_block_bytes": (4 * _KIB, 64 * _MIB),
            "random_block_bytes": (512, 1 * _MIB),
            "random_operations": (1, 100_000),
            "fsync_operations": (1, 1_000),
            "repetitions": (1, 10),
            "warmup_operations": (0, 10_000),
            "random_seed": (0, 2**63 - 1),
        }
        for field_name, (minimum, maximum) in integer_limits.items():
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{field_name} must be an integer")
            if not minimum <= value <= maximum:
                raise ValueError(f"{field_name} must be between {minimum} and {maximum}")

        if self.sequential_block_bytes > self.file_size_bytes:
            raise ValueError("sequential_block_bytes must not exceed file_size_bytes")
        if self.random_block_bytes > self.file_size_bytes:
            raise ValueError("random_block_bytes must not exceed file_size_bytes")

        estimated_bytes = self.file_size_bytes * (self.repetitions + 1)
        estimated_bytes += (
            self.random_block_bytes
            * (self.random_operations + self.fsync_operations)
            * self.repetitions
        )
        if estimated_bytes > 8 * _GIB:
            raise ValueError("estimated storage workload must not exceed 8 GiB")

    @classmethod
    def quick(cls) -> StorageProfileConfig:
        """Return a small workload suitable for smoke tests and CI."""

        return cls(
            file_size_bytes=8 * _MIB,
            sequential_block_bytes=1 * _MIB,
            random_block_bytes=4 * _KIB,
            random_operations=128,
            fsync_operations=3,
            repetitions=1,
            warmup_operations=4,
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
