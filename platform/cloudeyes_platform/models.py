"""Immutable ingestion receipt and persistence models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class IngestionReceipt:
    """Privacy-safe result returned for an accepted or duplicate bundle."""

    schema_version: str
    submission_id: str
    status: str
    received_at: datetime
    bundle_id: str
    bundle_sha256: str
    sample_count: int
    file_count: int
    warnings: tuple[str, ...] = field(default_factory=tuple)
    duplicate_of: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "bundle_sha256": self.bundle_sha256,
            "duplicate_of": self.duplicate_of,
            "file_count": self.file_count,
            "received_at": self.received_at.isoformat(),
            "sample_count": self.sample_count,
            "schema_version": self.schema_version,
            "status": self.status,
            "submission_id": self.submission_id,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class SampleRecord:
    """Canonical sample fields persisted for later cohort workers."""

    sample_id: str
    submission_id: str
    sample_path: str
    sample_sha256: str
    sample_json: str
    profile: str
    provider_id: str
    provider_name: str
    country_code: str | None
    product: str | None
    plan: str | None
    region: str | None
    zone: str | None
    machine_type: str
    cpu_count: int
    memory_bytes: int
    architecture: str
    protocol_version: str
    protocol_fingerprint: str
    quality_status: str
    created_at: str
    raw_evidence_count: int


__all__ = ["IngestionReceipt", "SampleRecord"]
