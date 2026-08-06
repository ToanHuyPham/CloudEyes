"""Statistical summaries for compatible cohorts."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from statistics import median

from ..models import Cohort, MeasurementStatus, MetricDirection
from ..statistics import SummaryStatistics, summarize


@dataclass(frozen=True, slots=True)
class MetricSummary:
    """Aggregated result for one normalized metric."""

    name: str
    unit: str
    direction: MetricDirection
    contributing_samples: int
    raw_observations: int
    statistics: SummaryStatistics


@dataclass(frozen=True, slots=True)
class CohortSummary:
    """Statistical summary of a complete cohort."""

    cohort_key: str
    provider_name: str
    total_samples: int
    metrics: tuple[MetricSummary, ...]


@dataclass(frozen=True, slots=True)
class _Observation:
    sample_id: str
    value: float
    unit: str
    direction: MetricDirection


def summarize_cohort(cohort: Cohort) -> CohortSummary:
    """Aggregate metrics while giving every sample equal weight."""

    observations: dict[str, list[_Observation]] = defaultdict(list)

    for sample in cohort.samples:
        for measurement in sample.measurements:
            if measurement.status is not MeasurementStatus.SUCCESS:
                continue
            for metric in measurement.metrics:
                observations[metric.name].append(
                    _Observation(
                        sample_id=sample.sample_id,
                        value=metric.value,
                        unit=metric.unit,
                        direction=metric.direction,
                    )
                )

    summaries: list[MetricSummary] = []
    for metric_name, metric_observations in observations.items():
        units = {item.unit for item in metric_observations}
        directions = {item.direction for item in metric_observations}
        if len(units) != 1:
            raise ValueError(f"metric {metric_name} contains incompatible units")
        if len(directions) != 1:
            raise ValueError(f"metric {metric_name} contains incompatible directions")

        values_by_sample: dict[str, list[float]] = defaultdict(list)
        for observation in metric_observations:
            values_by_sample[observation.sample_id].append(observation.value)

        sample_values = tuple(
            float(median(values)) for _, values in sorted(values_by_sample.items())
        )
        summaries.append(
            MetricSummary(
                name=metric_name,
                unit=next(iter(units)),
                direction=next(iter(directions)),
                contributing_samples=len(sample_values),
                raw_observations=len(metric_observations),
                statistics=summarize(sample_values),
            )
        )

    return CohortSummary(
        cohort_key=cohort.key.value,
        provider_name=cohort.provider_name,
        total_samples=cohort.sample_count,
        metrics=tuple(sorted(summaries, key=lambda item: item.name)),
    )
