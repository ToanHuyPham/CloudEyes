"""Build compatible cohorts from samples."""

from __future__ import annotations

from collections import defaultdict

from ..models import Cohort, CohortKey, Sample, SampleQualityStatus


def build_cohorts(
    samples: tuple[Sample, ...],
    *,
    include_invalid: bool = False,
) -> tuple[Cohort, ...]:
    """Group samples by strict compatibility key."""

    groups: dict[CohortKey, list[Sample]] = defaultdict(list)
    seen_ids: set[str] = set()

    for sample in samples:
        if sample.sample_id in seen_ids:
            raise ValueError(f"duplicate sample ID: {sample.sample_id}")
        seen_ids.add(sample.sample_id)

        if not include_invalid and sample.quality.status is SampleQualityStatus.INVALID:
            continue
        groups[CohortKey.from_sample(sample)].append(sample)

    cohorts: list[Cohort] = []
    for key, grouped_samples in groups.items():
        ordered = tuple(sorted(grouped_samples, key=lambda item: (item.created_at, item.sample_id)))
        cohorts.append(
            Cohort(
                key=key,
                samples=ordered,
                started_at=ordered[0].created_at,
                ended_at=ordered[-1].created_at,
                provider_name=ordered[0].provider.name,
            )
        )

    return tuple(sorted(cohorts, key=lambda item: item.key.value))
