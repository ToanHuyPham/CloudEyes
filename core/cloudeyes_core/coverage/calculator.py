"""Coverage calculation for CloudEyes cohorts."""

from __future__ import annotations

from cloudeyes_core.cohorts import CohortSummary
from cloudeyes_core.models import Cohort, Coverage


def _known(values: list[str | None]) -> tuple[str, ...]:
    """Normalize and return sorted known values."""

    normalized = {
        value.strip()
        for value in values
        if value is not None and value.strip()
    }

    return tuple(sorted(normalized))


def calculate_coverage(
    cohort: Cohort,
    summary: CohortSummary,
    *,
    expected_metrics: tuple[str, ...] = (),
) -> Coverage:
    """Calculate evidence coverage for one cohort."""

    observation_days = (
        cohort.ended_at.date() - cohort.started_at.date()
    ).days + 1

    available_metrics = tuple(
        metric.name
        for metric in summary.metrics
    )

    gaps: list[str] = []

    if cohort.sample_count < 3:
        gaps.append("insufficient_samples")

    if observation_days < 3:
        gaps.append("short_observation_period")

    regions = _known(
        [sample.product.region for sample in cohort.samples]
    )
    zones = _known(
        [sample.product.zone for sample in cohort.samples]
    )
    products = _known(
        [sample.product.product for sample in cohort.samples]
    )
    plans = _known(
        [sample.product.plan for sample in cohort.samples]
    )

    if not regions:
        gaps.append("region_unknown")

    if not zones:
        gaps.append("zone_unknown")

    missing_metrics = sorted(
        set(expected_metrics) - set(available_metrics)
    )

    gaps.extend(
        f"missing_metric:{metric_name}"
        for metric_name in missing_metrics
    )

    return Coverage(
        sample_count=cohort.sample_count,
        observation_days=observation_days,
        regions=regions,
        zones=zones,
        products=products,
        plans=plans,
        available_metrics=available_metrics,
        expected_metrics=expected_metrics,
        gaps=tuple(gaps),
    )
