"""Coverage calculation for cohorts."""

from __future__ import annotations

from ..cohorts import CohortSummary
from ..models import Cohort, Coverage


def _known(values: list[str | None]) -> tuple[str, ...]:
    normalized = {value.strip() for value in values if value is not None and value.strip()}
    return tuple(sorted(normalized))


def calculate_coverage(
    cohort: Cohort,
    summary: CohortSummary,
    *,
    expected_metrics: tuple[str, ...] = (),
) -> Coverage:
    """Calculate evidence coverage and explicit gaps for one cohort."""

    expected = tuple(sorted(set(expected_metrics)))
    available = tuple(metric.name for metric in summary.metrics)
    observation_days = (cohort.ended_at.date() - cohort.started_at.date()).days + 1

    regions = _known([sample.product.region for sample in cohort.samples])
    zones = _known([sample.product.zone for sample in cohort.samples])
    products = _known([sample.product.product for sample in cohort.samples])
    plans = _known([sample.product.plan for sample in cohort.samples])

    gaps: list[str] = []
    if cohort.sample_count < 3:
        gaps.append("insufficient_samples")
    if observation_days < 3:
        gaps.append("short_observation_period")
    if not regions:
        gaps.append("region_unknown")
    if not zones:
        gaps.append("zone_unknown")
    if not products:
        gaps.append("product_unknown")
    if not plans:
        gaps.append("plan_unknown")

    for metric_name in sorted(set(expected) - set(available)):
        gaps.append(f"missing_metric:{metric_name}")

    return Coverage(
        sample_count=cohort.sample_count,
        observation_days=observation_days,
        regions=regions,
        zones=zones,
        products=products,
        plans=plans,
        available_metrics=available,
        expected_metrics=expected,
        gaps=tuple(gaps),
    )
