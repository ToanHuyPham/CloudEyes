"""Compatibility checks for CloudEyes samples."""

from __future__ import annotations

from dataclasses import dataclass, field

from cloudeyes_core.models import CohortKey, Sample


@dataclass(frozen=True, slots=True)
class CompatibilityResult:
    """Result of comparing two samples."""

    compatible: bool
    differences: tuple[str, ...] = field(default_factory=tuple)


def compare_samples(
    first: Sample,
    second: Sample,
) -> CompatibilityResult:
    """Check whether two samples may belong to the same cohort."""

    first_key = CohortKey.from_sample(first)
    second_key = CohortKey.from_sample(second)

    differences: list[str] = []

    for field_name in first_key.__dataclass_fields__:
        first_value = getattr(first_key, field_name)
        second_value = getattr(second_key, field_name)

        if first_value != second_value:
            differences.append(field_name)

    return CompatibilityResult(
        compatible=not differences,
        differences=tuple(differences),
    )
