"""Validated configuration for CloudEyes Database Profile v1."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

_MIB = 1024 * 1024


@dataclass(frozen=True, slots=True)
class DatabaseProfileConfig:
    """Bounded local SQLite workload used by Database Profile v1."""

    version: str = "1.0.0"
    engine: str = "sqlite"
    record_count: int = 2_000
    payload_bytes: int = 256
    connection_operations: int = 15
    point_read_operations: int = 500
    insert_operations: int = 100
    update_operations: int = 100
    mixed_operations: int = 1_000
    mixed_read_percent: int = 80
    concurrency: int = 4
    warmup_operations: int = 100
    repetitions: int = 3
    busy_timeout_seconds: float = 5.0
    random_seed: int = 20_260_806
    journal_mode: str = "wal"
    synchronous: str = "full"

    def __post_init__(self) -> None:
        version = self.version.strip()
        if not version:
            raise ValueError("version must not be empty")
        object.__setattr__(self, "version", version)

        engine = self.engine.strip().lower()
        if engine != "sqlite":
            raise ValueError("Database Profile v1 supports only the sqlite engine")
        object.__setattr__(self, "engine", engine)

        journal_mode = self.journal_mode.strip().lower()
        if journal_mode != "wal":
            raise ValueError("journal_mode must be wal for protocol version 1.0.0")
        object.__setattr__(self, "journal_mode", journal_mode)

        synchronous = self.synchronous.strip().lower()
        if synchronous != "full":
            raise ValueError("synchronous must be full for protocol version 1.0.0")
        object.__setattr__(self, "synchronous", synchronous)

        integer_bounds = (
            ("record_count", 100, 100_000),
            ("payload_bytes", 32, 4_096),
            ("connection_operations", 1, 100),
            ("point_read_operations", 1, 100_000),
            ("insert_operations", 1, 10_000),
            ("update_operations", 1, 10_000),
            ("mixed_operations", 10, 100_000),
            ("mixed_read_percent", 50, 95),
            ("concurrency", 1, 32),
            ("warmup_operations", 0, 10_000),
            ("repetitions", 1, 10),
            ("random_seed", 0, 2_147_483_647),
        )
        for field_name, minimum, maximum in integer_bounds:
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{field_name} must be an integer")
            if not minimum <= value <= maximum:
                raise ValueError(f"{field_name} must be between {minimum} and {maximum}")

        if self.concurrency > self.mixed_operations:
            raise ValueError("concurrency must not exceed mixed_operations")
        if self.record_count * self.payload_bytes > 128 * _MIB:
            raise ValueError("seed payload must not exceed 128 MiB")

        operations_per_repetition = (
            self.connection_operations
            + self.point_read_operations
            + self.insert_operations
            + self.update_operations
            + self.mixed_operations
        )
        if operations_per_repetition * self.repetitions > 500_000:
            raise ValueError("total bounded database operations must not exceed 500000")

        if isinstance(self.busy_timeout_seconds, bool) or not isinstance(
            self.busy_timeout_seconds, int | float
        ):
            raise TypeError("busy_timeout_seconds must be numeric")
        busy_timeout = float(self.busy_timeout_seconds)
        if not 0.1 <= busy_timeout <= 30.0:
            raise ValueError("busy_timeout_seconds must be between 0.1 and 30")
        object.__setattr__(self, "busy_timeout_seconds", busy_timeout)

    @classmethod
    def quick(cls, *, concurrency: int = 2) -> DatabaseProfileConfig:
        """Return a small workload suitable for CI and smoke tests."""

        return cls(
            record_count=200,
            payload_bytes=128,
            connection_operations=5,
            point_read_operations=50,
            insert_operations=10,
            update_operations=10,
            mixed_operations=100,
            mixed_read_percent=80,
            concurrency=concurrency,
            warmup_operations=10,
            repetitions=1,
            busy_timeout_seconds=2.0,
        )

    @property
    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 protocol fingerprint."""

        encoded = json.dumps(
            asdict(self),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
