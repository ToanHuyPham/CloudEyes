"""Provider scorecard construction."""

from __future__ import annotations

from statistics import fmean

from ..models import (
    AssessmentDimension,
    AssessmentStatus,
    Cohort,
    DimensionAssessment,
    NormalizedPriceEvidence,
    PeerMetricComparison,
    ProviderReport,
    ProviderScorecard,
    ValueMetricComparison,
)
from .consistency import assess_consistency
from .performance import assess_performance
from .reliability import assess_reliability, successful_measurement_ratio
from .value import assess_value


def _evidence_dimension(report: ProviderReport) -> DimensionAssessment:
    coverage_ratios = [item.coverage.metric_ratio for item in report.cohorts]
    coverage_ratio = fmean(coverage_ratios) if coverage_ratios else 0.0
    limitations = tuple(sorted(set(report.gaps)))
    return DimensionAssessment(
        dimension=AssessmentDimension.EVIDENCE,
        status=AssessmentStatus.ASSESSED,
        level=report.overall_confidence,
        rule_id="evidence.minimum_confidence.v1",
        summary=(
            f"Evidence confidence is {report.overall_confidence.value}; "
            f"mean expected-metric coverage is {coverage_ratio:.1%}."
        ),
        evidence_refs=tuple(item.cohort_id for item in report.cohorts),
        limitations=limitations,
    )


def build_scorecard(
    report: ProviderReport,
    cohorts: tuple[Cohort, ...],
    peer_comparisons: tuple[PeerMetricComparison, ...] = (),
    pricing_evidence: tuple[NormalizedPriceEvidence, ...] = (),
    value_comparisons: tuple[ValueMetricComparison, ...] = (),
) -> ProviderScorecard:
    """Build a multidimensional scorecard without a universal provider score."""

    coverage_ratios = [item.coverage.metric_ratio for item in report.cohorts]
    coverage_ratio = fmean(coverage_ratios) if coverage_ratios else 0.0
    profiles = tuple(sorted({item.protocol.profile for item in report.cohorts}))
    dimensions = (
        _evidence_dimension(report),
        assess_consistency(report),
        assess_reliability(cohorts),
        assess_performance(report, peer_comparisons),
        assess_value(pricing_evidence, value_comparisons),
    )
    return ProviderScorecard(
        sample_count=report.total_samples,
        cohort_count=report.cohort_count,
        profile_count=len(profiles),
        profiles=profiles,
        coverage_ratio=coverage_ratio,
        successful_measurement_ratio=successful_measurement_ratio(cohorts),
        dimensions=dimensions,
    )
