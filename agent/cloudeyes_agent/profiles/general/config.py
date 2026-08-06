"""Validated configuration for the built-in General Profile."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

_MIB = 1024 * 1024


@dataclass(frozen=True, slots=True)
class GeneralProfileConfig:
    """Bounded workload sizes for a safe, portable local benchmark."""

    version: str = "1.0.0"
    cpu_block_bytes: int = 64 * 1024
    cpu_iterations: int = 1024
    memory_block_bytes: int = 8 * _MIB
    memory_iterations: int = 16
    storage_block_bytes: int = 4 * _MIB
    storage_iterations: int = 4
    include_storage: bool = True
    fsync_storage: bool = True

    def __post_init__(self) -> None:
        version = self.version.strip()
        if not version:
            raise ValueError("version must not be empty")
        object.__setattr__(self, "version", version)

        if not isinstance(self.include_storage, bool):
            raise TypeError("include_storage must be a boolean")
        if not isinstance(self.fsync_storage, bool):
            raise TypeError("fsync_storage must be a boolean")

        limits = {
            "cpu_block_bytes": (1, 1 * _MIB),
            "cpu_iterations": (1, 20_000),
            "memory_block_bytes": (1, 64 * _MIB),
            "memory_iterations": (1, 1024),
            "storage_block_bytes": (1, 64 * _MIB),
            "storage_iterations": (1, 256),
        }
        for field_name, (minimum, maximum) in limits.items():
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{field_name} must be an integer")
            if not minimum <= value <= maximum:
                raise ValueError(f"{field_name} must be between {minimum} and {maximum}")

        total_cpu_bytes = self.cpu_block_bytes * self.cpu_iterations
        if total_cpu_bytes > 1024 * _MIB:
            raise ValueError("CPU workload must not exceed 1 GiB")

        total_memory_bytes = self.memory_block_bytes * self.memory_iterations
        if total_memory_bytes > 4096 * _MIB:
            raise ValueError("memory workload must not exceed 4 GiB")

        total_storage_bytes = self.storage_block_bytes * self.storage_iterations
        if total_storage_bytes > 512 * _MIB:
            raise ValueError("storage workload must not exceed 512 MiB")

    @classmethod
    def quick(cls, *, include_storage: bool = True) -> GeneralProfileConfig:
        """Return a small configuration intended for smoke tests and CI."""

        return cls(
            cpu_block_bytes=16 * 1024,
            cpu_iterations=128,
            memory_block_bytes=1 * _MIB,
            memory_iterations=4,
            storage_block_bytes=512 * 1024,
            storage_iterations=2,
            include_storage=include_storage,
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
