"""Provider report output models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .confidence import Confidence, ConfidenceLevel
from .coverage import Coverage
from .protocol import ProtocolIdentity


@dataclass(frozen=True, slots=True)
class CohortReport:
    """One analyzed cohort inside a provider report."""

    cohort_id: str
    cohort_key: str
    protocol: ProtocolIdentity
    started_at: datetime
    ended_at: datetime
    sample_count: int
    sample_ids: tuple[str, ...]
    coverage: Coverage
    confidence: Confidence
    metrics: tuple[object, ...]

    def __post_init__(self) -> None:
        if not self.cohort_id.strip() or not self.cohort_key.strip():
            raise ValueError("cohort report identifiers must not be empty")
        if self.started_at.tzinfo is None or self.ended_at.tzinfo is None:
            raise ValueError("cohort report timestamps must contain timezone information")
        if self.ended_at < self.started_at:
            raise ValueError("cohort report ended_at must not precede started_at")
        if self.sample_count != len(self.sample_ids):
            raise ValueError("sample_count must match sample_ids")


@dataclass(frozen=True, slots=True)
class ProviderReport:
    """Complete report for one provider across one or more cohorts."""

    schema_version: str
    report_id: str
    generated_at: datetime
    provider_id: str
    provider_name: str
    total_samples: int
    cohort_count: int
    overall_confidence: ConfidenceLevel
    gaps: tuple[str, ...]
    cohorts: tuple[CohortReport, ...]

    def __post_init__(self) -> None:
        for field_name in ("schema_version", "report_id", "provider_id", "provider_name"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} must not be empty")
        if self.generated_at.tzinfo is None:
            raise ValueError("generated_at must contain timezone information")
        if self.cohort_count != len(self.cohorts):
            raise ValueError("cohort_count must match cohorts")
        if self.total_samples != sum(item.sample_count for item in self.cohorts):
            raise ValueError("total_samples must match cohort sample counts")
