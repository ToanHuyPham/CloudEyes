"""Compatible peer price-performance comparison."""

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
    NormalizedPriceEvidence,
    PeerComparisonOutcome,
    ProviderReport,
    ValueIndexDefinition,
    ValueMetricComparison,
)
from ..provider.comparison import COMPARISON_THRESHOLD_PERCENT, PeerKey
from .effective_cost import value_index


@dataclass(frozen=True, slots=True)
class _ProviderValueMetric:
    value_index: float
    hourly_usd: float
    definition: ValueIndexDefinition
    cohort_ids: tuple[str, ...]
    pricing_evidence_ids: tuple[str, ...]
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


def _provider_value_metrics(
    cohorts: tuple[Cohort, ...],
    cohort_reports: dict[str, CohortReport],
    cohort_evidence: dict[str, NormalizedPriceEvidence],
) -> dict[str, dict[tuple[str, str, MetricDirection], _ProviderValueMetric]]:
    observations: dict[
        str,
        dict[
            tuple[str, str, MetricDirection],
            list[
                tuple[
                    float,
                    float,
                    ValueIndexDefinition,
                    str,
                    str,
                    ConfidenceLevel,
                    ConfidenceLevel,
                ]
            ],
        ],
    ] = defaultdict(lambda: defaultdict(list))

    for cohort in cohorts:
        price = cohort_evidence.get(cohort.key.value)
        if price is None:
            continue
        report = cohort_reports[cohort.key.value]
        for metric in report.metrics:
            index = value_index(metric.statistics.median, price.hourly_usd, metric.direction)
            if index is None:
                continue
            index_value, definition = index
            key = (metric.name, metric.unit, metric.direction)
            observations[cohort.key.provider_id][key].append(
                (
                    index_value,
                    price.hourly_usd,
                    definition,
                    report.cohort_id,
                    price.pricing_evidence_id,
                    report.confidence.overall,
                    price.confidence,
                )
            )

    result: dict[str, dict[tuple[str, str, MetricDirection], _ProviderValueMetric]] = {}
    for provider_id, metrics in observations.items():
        result[provider_id] = {}
        for metric_key, values in metrics.items():
            definitions = {item[2] for item in values}
            if len(definitions) != 1:
                raise ValueError("inconsistent value-index definitions for one metric")
            result[provider_id][metric_key] = _ProviderValueMetric(
                value_index=float(median(item[0] for item in values)),
                hourly_usd=float(median(item[1] for item in values)),
                definition=next(iter(definitions)),
                cohort_ids=tuple(sorted(item[3] for item in values)),
                pricing_evidence_ids=tuple(sorted({item[4] for item in values})),
                confidences=tuple(
                    confidence for item in values for confidence in (item[5], item[6])
                ),
            )
    return result


def build_value_comparisons(
    cohorts: tuple[Cohort, ...],
    reports: tuple[ProviderReport, ...],
    cohort_evidence: dict[str, NormalizedPriceEvidence],
) -> dict[str, tuple[ValueMetricComparison, ...]]:
    """Build equal-provider-weight value comparisons for priced compatible cohorts."""

    cohort_reports = _cohort_reports_by_key(reports)
    groups: dict[PeerKey, list[Cohort]] = defaultdict(list)
    for cohort in cohorts:
        if (
            cohort.key.provider_id == "unknown"
            or cohort.key.country_code == "unknown"
            or cohort.key.value not in cohort_evidence
        ):
            continue
        groups[PeerKey.from_cohort(cohort)].append(cohort)

    comparisons: dict[str, list[ValueMetricComparison]] = defaultdict(list)
    for peer_key, grouped in sorted(groups.items(), key=lambda item: item[0].value):
        providers = {item.key.provider_id for item in grouped}
        if len(providers) < 2:
            continue

        peer_group_id = _identifier("peer-group", (peer_key.value,))
        provider_metrics = _provider_value_metrics(tuple(grouped), cohort_reports, cohort_evidence)
        metric_keys = sorted(
            {metric_key for metrics in provider_metrics.values() for metric_key in metrics},
            key=lambda item: (item[0], item[1], item[2].value),
        )

        for metric_name, metric_unit, direction in metric_keys:
            available = {
                provider_id: metrics[(metric_name, metric_unit, direction)]
                for provider_id, metrics in provider_metrics.items()
                if (metric_name, metric_unit, direction) in metrics
            }
            if len(available) < 2:
                continue

            for provider_id, provider_metric in sorted(available.items()):
                peer_metrics = {
                    peer_id: metric
                    for peer_id, metric in available.items()
                    if peer_id != provider_id
                }
                peer_value_index = float(median(item.value_index for item in peer_metrics.values()))
                if peer_value_index <= 0:
                    continue
                difference = (
                    (provider_metric.value_index - peer_value_index) / peer_value_index * 100.0
                )
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
                peer_price_ids = tuple(
                    sorted(
                        {
                            price_id
                            for metric in peer_metrics.values()
                            for price_id in metric.pricing_evidence_ids
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
                    "value-comparison",
                    (
                        peer_group_id,
                        provider_id,
                        metric_name,
                        metric_unit,
                        direction.value,
                    ),
                )
                comparisons[provider_id].append(
                    ValueMetricComparison(
                        comparison_id=comparison_id,
                        peer_group_id=peer_group_id,
                        peer_key=peer_key.value,
                        profile=peer_key.profile,
                        metric_name=metric_name,
                        metric_unit=metric_unit,
                        metric_direction=direction,
                        index_definition=provider_metric.definition,
                        provider_hourly_usd=provider_metric.hourly_usd,
                        peer_hourly_usd_median=float(
                            median(item.hourly_usd for item in peer_metrics.values())
                        ),
                        provider_value_index=provider_metric.value_index,
                        peer_value_index_median=peer_value_index,
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
                        provider_pricing_evidence_ids=(provider_metric.pricing_evidence_ids),
                        peer_pricing_evidence_ids=peer_price_ids,
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
