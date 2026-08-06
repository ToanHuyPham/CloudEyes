"""Build cohorts from validated CloudEyes samples."""

from __future__ import annotations

from collections import defaultdict

from cloudeyes_core.models import Cohort, CohortKey, Sample


def build_cohorts(samples: tuple[Sample, ...]) -> tuple[Cohort, ...]:
    """Group samples by their compatibility key."""

    if not samples:
        return ()

    groups: dict[CohortKey, list[Sample]] = defaultdict(list)

    for sample in samples:
        groups[CohortKey.from_sample(sample)].append(sample)

    cohorts: list[Cohort] = []

    for key, grouped_samples in groups.items():
        ordered_samples = tuple(
            sorted(
                grouped_samples,
                key=lambda sample: sample.created_at,
            )
        )

        cohorts.append(
            Cohort(
                key=key,
                samples=ordered_samples,
                started_at=ordered_samples[0].created_at,
                ended_at=ordered_samples[-1].created_at,
                provider_name=ordered_samples[0].provider.name,
            )
        )

    return tuple(
        sorted(
            cohorts,
            key=lambda cohort: cohort.key.value,
        )
    )
