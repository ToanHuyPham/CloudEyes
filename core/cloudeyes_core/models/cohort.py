"""Cohort models used to group compatible CloudEyes samples."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .sample import Sample


def _normalize(value: str | None) -> str:
    if value is None:
        return "unknown"

    cleaned = value.strip().lower()
    return cleaned or "unknown"


@dataclass(frozen=True, slots=True)
class CohortKey:
    """Stable key defining which samples may be analyzed together."""

    provider_id: str
    country_code: str
    product: str
    plan: str
    region: str
    zone: str
    machine_type: str
    architecture: str
    profile: str
    protocol_version: str
    protocol_fingerprint: str

    @classmethod
    def from_sample(cls, sample: Sample) -> "CohortKey":
        """Create a cohort key from one sample."""

        return cls(
            provider_id=_normalize(sample.provider.provider_id),
            country_code=_normalize(sample.provider.country_code),
            product=_normalize(sample.product.product),
            plan=_normalize(sample.product.plan),
            region=_normalize(sample.product.region),
            zone=_normalize(sample.product.zone),
            machine_type=_normalize(sample.machine.machine_type),
            architecture=_normalize(sample.machine.architecture),
            profile=_normalize(sample.protocol.profile),
            protocol_version=_normalize(sample.protocol.version),
            protocol_fingerprint=_normalize(sample.protocol.fingerprint),
        )

    @property
    def value(self) -> str:
        """Return a deterministic human-readable cohort key."""

        parts = (
            self.provider_id,
            self.country_code,
            self.product,
            self.plan,
            self.region,
            self.zone,
            self.machine_type,
            self.architecture,
            self.profile,
            self.protocol_version,
            self.protocol_fingerprint,
        )

        return "|".join(parts)


@dataclass(frozen=True, slots=True)
class Cohort:
    """A group of compatible samples."""

    key: CohortKey
    samples: tuple[Sample, ...]
    started_at: datetime
    ended_at: datetime
    provider_name: str
    sample_count: int = field(init=False)

    def __post_init__(self) -> None:
        if not self.samples:
            raise ValueError("cohort must contain at least one sample")

        if self.ended_at < self.started_at:
            raise ValueError("ended_at must not be earlier than started_at")

        for sample in self.samples:
            if CohortKey.from_sample(sample) != self.key:
                raise ValueError(
                    f"sample {sample.sample_id} is incompatible with cohort"
                )

        object.__setattr__(self, "sample_count", len(self.samples))
