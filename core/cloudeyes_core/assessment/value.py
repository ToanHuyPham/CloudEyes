"""Normalized price-performance assessment guardrails."""

from __future__ import annotations

from collections import Counter

from ..models import (
    AssessmentDimension,
    AssessmentStatus,
    ConfidenceLevel,
    DimensionAssessment,
    NormalizedPriceEvidence,
    PeerComparisonOutcome,
    ValueMetricComparison,
)


def assess_value(
    pricing_evidence: tuple[NormalizedPriceEvidence, ...] = (),
    comparisons: tuple[ValueMetricComparison, ...] = (),
) -> DimensionAssessment:
    """Assess value only from normalized pricing and compatible peer evidence."""

    if not pricing_evidence:
        return DimensionAssessment(
            dimension=AssessmentDimension.VALUE,
            status=AssessmentStatus.NOT_ASSESSED,
            level=None,
            rule_id="value.normalized_price_required.v1",
            summary=(
                "Value was not assessed because no normalized pricing evidence matched the "
                "analyzed cohorts."
            ),
            limitations=("normalized_pricing_required",),
        )

    if not comparisons:
        return DimensionAssessment(
            dimension=AssessmentDimension.VALUE,
            status=AssessmentStatus.NOT_ASSESSED,
            level=None,
            rule_id="value.compatible_priced_peer_required.v1",
            summary=(
                "Pricing was normalized, but value was not graded because no compatible priced "
                "peer baseline was available."
            ),
            evidence_refs=tuple(item.pricing_evidence_id for item in pricing_evidence),
            limitations=("compatible_priced_peer_baseline_required",),
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
        limitations.append(f"low_confidence_value_comparisons:{low_confidence}")
    if single_peer:
        limitations.append(f"single_peer_value_baselines:{single_peer}")

    return DimensionAssessment(
        dimension=AssessmentDimension.VALUE,
        status=AssessmentStatus.ASSESSED,
        level=level,
        rule_id="value.compatible_peer_price_performance.v1",
        summary=(
            f"Across {len(comparisons)} normalized price-performance metrics at the 5% "
            f"similarity threshold: {ahead} ahead, {similar} similar, and {behind} behind."
        ),
        evidence_refs=tuple(item.comparison_id for item in comparisons),
        limitations=tuple(limitations),
    )
