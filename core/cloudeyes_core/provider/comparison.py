"""Strict, equal-weight comparison of compatible provider cohorts."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass
from statistics import median

from ..models import (
    Cohort,
    CohortReport,
    ConfidenceLevel,
    MetricDirection,
    PeerComparisonOutcome,
    PeerMetricComparison,
    ProviderReport,
)

COMPARISON_THRESHOLD_PERCENT = 5.0


@dataclass(frozen=True, slots=True)
class PeerKey:
    """Cross-provider compatibility key.

    Product, plan, region, and zone names are provider-specific labels and are therefore
    excluded. Hardware, geography, profile, and protocol identity remain exact.
    """

    country_code: str
    machine_type: str
    cpu_count: int
    memory_bytes: int
    architecture: str
    profile: str
    protocol_version: str
    protocol_fingerprint: str

    @classmethod
    def from_cohort(cls, cohort: Cohort) -> PeerKey:
        """Build a strict cross-provider key from one cohort."""

        key = cohort.key
        return cls(
            country_code=key.country_code,
            machine_type=key.machine_type,
            cpu_count=key.cpu_count,
            memory_bytes=key.memory_bytes,
            architecture=key.architecture,
            profile=key.profile,
            protocol_version=key.protocol_version,
            protocol_fingerprint=key.protocol_fingerprint,
        )

    @property
    def value(self) -> str:
        """Return a deterministic serialized peer key."""

        return "|".join(
            (
                self.country_code,
                self.machine_type,
                str(self.cpu_count),
                str(self.memory_bytes),
                self.architecture,
                self.profile,
                self.protocol_version,
                self.protocol_fingerprint,
            )
        )


@dataclass(frozen=True, slots=True)
class _ProviderMetric:
    value: float
    cohort_ids: tuple[str, ...]
    confidences: tuple[ConfidenceLevel, ...]


def _identifier(prefix: str, parts: tuple[str, ...]) -> str:
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _minimum_confidence(values: tuple[ConfidenceLevel, ...]) -> ConfidenceLevel:
    order = {
        ConfidenceLevel.LOW: 0,
        ConfidenceLevel.MEDIUM: 1,
        ConfidenceLevel.HIGH: 2,
    }
    return min(values, key=order.__getitem__)


def _comparison_confidence(
    confidences: tuple[ConfidenceLevel, ...],
    *,
    peer_provider_count: int,
) -> ConfidenceLevel:
    minimum = _minimum_confidence(confidences)
    if peer_provider_count >= 2 and minimum is ConfidenceLevel.HIGH:
        return ConfidenceLevel.HIGH
    if minimum in (ConfidenceLevel.MEDIUM, ConfidenceLevel.HIGH):
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


def _relative_difference(
    provider_value: float,
    peer_median: float,
    direction: MetricDirection,
) -> float | None:
    if peer_median == 0:
        return None
    raw = (provider_value - peer_median) / abs(peer_median) * 100.0
    return -raw if direction is MetricDirection.LOWER_IS_BETTER else raw


def _outcome(relative_difference_percent: float) -> PeerComparisonOutcome:
    if relative_difference_percent >= COMPARISON_THRESHOLD_PERCENT:
        return PeerComparisonOutcome.AHEAD
    if relative_difference_percent <= -COMPARISON_THRESHOLD_PERCENT:
        return PeerComparisonOutcome.BEHIND
    return PeerComparisonOutcome.SIMILAR


def _cohort_reports_by_key(
    reports: tuple[ProviderReport, ...],
) -> dict[str, CohortReport]:
    result: dict[str, CohortReport] = {}
    for report in reports:
        for cohort in report.cohorts:
            if cohort.cohort_key in result:
                raise ValueError(f"duplicate cohort report key: {cohort.cohort_key}")
            result[cohort.cohort_key] = cohort
    return result


def _provider_metrics(
    cohorts: tuple[Cohort, ...],
    cohort_reports: dict[str, CohortReport],
) -> dict[str, dict[tuple[str, str, MetricDirection], _ProviderMetric]]:
    observations: dict[
        str,
        dict[tuple[str, str, MetricDirection], list[tuple[float, str, ConfidenceLevel]]],
    ] = defaultdict(lambda: defaultdict(list))

    for cohort in cohorts:
        report = cohort_reports[cohort.key.value]
        for metric in report.metrics:
            key = (metric.name, metric.unit, metric.direction)
            observations[cohort.key.provider_id][key].append(
                (metric.statistics.median, report.cohort_id, report.confidence.overall)
            )

    result: dict[str, dict[tuple[str, str, MetricDirection], _ProviderMetric]] = {}
    for provider_id, metrics in observations.items():
        result[provider_id] = {}
        for metric_key, values in metrics.items():
            result[provider_id][metric_key] = _ProviderMetric(
                value=float(median(item[0] for item in values)),
                cohort_ids=tuple(sorted(item[1] for item in values)),
                confidences=tuple(item[2] for item in values),
            )
    return result


def build_peer_comparisons(
    cohorts: tuple[Cohort, ...],
    reports: tuple[ProviderReport, ...],
) -> dict[str, tuple[PeerMetricComparison, ...]]:
    """Compare compatible provider cohorts without weighting by sample or cohort count."""

    cohort_reports = _cohort_reports_by_key(reports)
    groups: dict[PeerKey, list[Cohort]] = defaultdict(list)
    for cohort in cohorts:
        # Unknown provider or geography cannot support a defensible cross-provider baseline.
        if cohort.key.provider_id == "unknown" or cohort.key.country_code == "unknown":
            continue
        groups[PeerKey.from_cohort(cohort)].append(cohort)

    comparisons: dict[str, list[PeerMetricComparison]] = defaultdict(list)
    for peer_key, grouped in sorted(groups.items(), key=lambda item: item[0].value):
        providers = {item.key.provider_id for item in grouped}
        if len(providers) < 2:
            continue

        peer_group_id = _identifier("peer-group", (peer_key.value,))
        provider_metrics = _provider_metrics(tuple(grouped), cohort_reports)
        metric_keys = sorted(
            {metric_key for metrics in provider_metrics.values() for metric_key in metrics},
            key=lambda item: (item[0], item[1], item[2].value),
        )

        for metric_name, unit, direction in metric_keys:
            if direction is MetricDirection.NEUTRAL:
                continue
            available = {
                provider_id: metrics[(metric_name, unit, direction)]
                for provider_id, metrics in provider_metrics.items()
                if (metric_name, unit, direction) in metrics
            }
            if len(available) < 2:
                continue

            for provider_id, provider_metric in sorted(available.items()):
                peer_metrics = {
                    peer_id: metric
                    for peer_id, metric in available.items()
                    if peer_id != provider_id
                }
                peer_median = float(median(item.value for item in peer_metrics.values()))
                difference = _relative_difference(
                    provider_metric.value,
                    peer_median,
                    direction,
                )
                if difference is None:
                    continue

                peer_provider_ids = tuple(sorted(peer_metrics))
                peer_cohort_ids = tuple(
                    sorted(
                        {
                            cohort_id
                            for metric in peer_metrics.values()
                            for cohort_id in metric.cohort_ids
                        }
                    )
                )
                confidences = (
                    *provider_metric.confidences,
                    *(
                        confidence
                        for metric in peer_metrics.values()
                        for confidence in metric.confidences
                    ),
                )
                comparison_id = _identifier(
                    "peer-comparison",
                    (
                        peer_group_id,
                        provider_id,
                        metric_name,
                        unit,
                        direction.value,
                    ),
                )
                comparisons[provider_id].append(
                    PeerMetricComparison(
                        comparison_id=comparison_id,
                        peer_group_id=peer_group_id,
                        peer_key=peer_key.value,
                        profile=peer_key.profile,
                        metric_name=metric_name,
                        unit=unit,
                        direction=direction,
                        provider_value=provider_metric.value,
                        peer_median=peer_median,
                        relative_difference_percent=difference,
                        outcome=_outcome(difference),
                        confidence=_comparison_confidence(
                            confidences,
                            peer_provider_count=len(peer_provider_ids),
                        ),
                        peer_provider_count=len(peer_provider_ids),
                        peer_provider_ids=peer_provider_ids,
                        provider_cohort_ids=provider_metric.cohort_ids,
                        peer_cohort_ids=peer_cohort_ids,
                    )
                )

    return {
        provider_id: tuple(
            sorted(
                items,
                key=lambda item: (item.peer_group_id, item.metric_name, item.comparison_id),
            )
        )
        for provider_id, items in comparisons.items()
    }
