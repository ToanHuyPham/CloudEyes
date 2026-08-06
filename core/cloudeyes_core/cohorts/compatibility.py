"""Compatibility comparison for samples."""

from __future__ import annotations

from dataclasses import dataclass, field, fields

from ..models import CohortKey, Sample


@dataclass(frozen=True, slots=True)
class CompatibilityResult:
    """Result of comparing two sample cohort keys."""

    compatible: bool
    differences: tuple[str, ...] = field(default_factory=tuple)


def compare_samples(first: Sample, second: Sample) -> CompatibilityResult:
    """Check whether two samples may belong to the same cohort."""

    first_key = CohortKey.from_sample(first)
    second_key = CohortKey.from_sample(second)
    differences = tuple(
        item.name
        for item in fields(CohortKey)
        if getattr(first_key, item.name) != getattr(second_key, item.name)
    )
    return CompatibilityResult(compatible=not differences, differences=differences)
