"""Cohort key helpers."""

from __future__ import annotations

from cloudeyes_core.models import CohortKey, Sample


def build_cohort_key(sample: Sample) -> CohortKey:
    """Build the compatibility key for a sample."""

    return CohortKey.from_sample(sample)
