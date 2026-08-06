"""Cohort key helper."""

from __future__ import annotations

from ..models import CohortKey, Sample


def build_cohort_key(sample: Sample) -> CohortKey:
    """Build the strict compatibility key for a sample."""

    return CohortKey.from_sample(sample)
