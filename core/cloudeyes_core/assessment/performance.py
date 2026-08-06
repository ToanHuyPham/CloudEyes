"""Performance assessment using strict compatible peer evidence."""

from __future__ import annotations

from collections import Counter

from ..models import (
    AssessmentDimension,
    AssessmentStatus,
    ConfidenceLevel,
    DimensionAssessment,
    PeerComparisonOutcome,
    PeerMetricComparison,
    ProviderReport,
)


def assess_performance(
    report: ProviderReport,
    comparisons: tuple[PeerMetricComparison, ...] = (),
) -> DimensionAssessment:
    """Assess only direction-adjusted metrics with a compatible peer baseline."""

    if not comparisons:
        return DimensionAssessment(
            dimension=AssessmentDimension.PERFORMANCE,
            status=AssessmentStatus.NOT_ASSESSED,
            level=None,
            rule_id="performance.compatible_peer_required.v1",
            summary=(
                "Performance was measured but not graded because no compatible peer baseline "
                "was available."
            ),
            evidence_refs=tuple(item.cohort_id for item in report.cohorts),
            limitations=("compatible_peer_baseline_required",),
        )

    counts = Counter(item.outcome for item in comparisons)
    ahead = counts[PeerComparisonOutcome.AHEAD]
    similar = counts[PeerComparisonOutcome.SIMILAR]
    behind = counts[PeerComparisonOutcome.BEHIND]
    if ahead > behind:
        level = ConfidenceLevel.HIGH
    elif behind > ahead:
        level = ConfidenceLevel.LOW
    else:
        level = ConfidenceLevel.MEDIUM

    limitations: list[str] = []
    low_confidence = sum(item.confidence is ConfidenceLevel.LOW for item in comparisons)
    single_peer = sum(item.peer_provider_count == 1 for item in comparisons)
    if low_confidence:
        limitations.append(f"low_confidence_peer_comparisons:{low_confidence}")
    if single_peer:
        limitations.append(f"single_peer_baselines:{single_peer}")

    return DimensionAssessment(
        dimension=AssessmentDimension.PERFORMANCE,
        status=AssessmentStatus.ASSESSED,
        level=level,
        rule_id="performance.compatible_peer_relative.v1",
        summary=(
            f"Across {len(comparisons)} compatible peer metrics at the 5% similarity "
            f"threshold: {ahead} ahead, {similar} similar, and {behind} behind."
        ),
        evidence_refs=tuple(item.comparison_id for item in comparisons),
        limitations=tuple(limitations),
    )
