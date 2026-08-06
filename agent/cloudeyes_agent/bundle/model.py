"""Immutable models for CloudEyes result bundles and submission receipts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class BundleFile:
    """One checksummed payload stored inside a result bundle."""

    path: str
    sha256: str
    size_bytes: int
    media_type: str
    redaction_count: int = 0


@dataclass(frozen=True, slots=True)
class BundleSample:
    """Manifest entry describing one bundled sample and its evidence."""

    sample_id: str
    profile: str
    sample_path: str
    raw_evidence_paths: tuple[str, ...] = field(default_factory=tuple)
    validation_warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class BundleVerification:
    """Integrity and semantic verification result for one result bundle."""

    bundle_id: str
    bundle_sha256: str
    sample_count: int
    file_count: int
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class SubmissionReceipt:
    """Privacy-safe receipt produced after an HTTP submission attempt."""

    schema_version: str
    submitted_at: datetime
    endpoint: str
    bundle_id: str
    bundle_sha256: str
    status_code: int
    accepted: bool
    remote_submission_id: str | None
    response_sha256: str


__all__ = [
    "BundleFile",
    "BundleSample",
    "BundleVerification",
    "SubmissionReceipt",
]
