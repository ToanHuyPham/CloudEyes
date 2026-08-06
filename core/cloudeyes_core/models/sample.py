"""Immutable CloudEyes sample model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from .identity import MachineIdentity, ProductIdentity, ProviderIdentity
from .measurement import Measurement
from .protocol import ProtocolIdentity


class SampleQualityStatus(StrEnum):
    """Overall validity assigned during collection."""

    VALID = "valid"
    VALID_WITH_WARNINGS = "valid_with_warnings"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class SampleQuality:
    """Collection-time quality result."""

    status: SampleQualityStatus
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        status = (
            self.status
            if isinstance(self.status, SampleQualityStatus)
            else SampleQualityStatus(self.status)
        )
        warnings = tuple(item.strip() for item in self.warnings if item.strip())
        errors = tuple(item.strip() for item in self.errors if item.strip())

        object.__setattr__(self, "status", status)
        object.__setattr__(self, "warnings", warnings)
        object.__setattr__(self, "errors", errors)

        if status is SampleQualityStatus.INVALID and not errors:
            raise ValueError("invalid samples must contain at least one error")


@dataclass(frozen=True, slots=True)
class Sample:
    """One complete provider-assessment sample."""

    sample_id: str
    created_at: datetime
    provider: ProviderIdentity
    product: ProductIdentity
    machine: MachineIdentity
    protocol: ProtocolIdentity
    measurements: tuple[Measurement, ...]
    quality: SampleQuality

    def __post_init__(self) -> None:
        sample_id = self.sample_id.strip()
        if not sample_id:
            raise ValueError("sample_id must not be empty")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must contain timezone information")
        if not self.measurements:
            raise ValueError("sample must contain at least one measurement")

        object.__setattr__(self, "sample_id", sample_id)
        object.__setattr__(self, "measurements", tuple(self.measurements))

    @classmethod
    def create(
        cls,
        *,
        sample_id: str,
        provider: ProviderIdentity,
        product: ProductIdentity,
        machine: MachineIdentity,
        protocol: ProtocolIdentity,
        measurements: tuple[Measurement, ...],
        quality: SampleQuality,
    ) -> "Sample":
        """Create a sample using the current UTC time."""

        return cls(
            sample_id=sample_id,
            created_at=datetime.now(UTC),
            provider=provider,
            product=product,
            machine=machine,
            protocol=protocol,
            measurements=measurements,
            quality=quality,
        )
