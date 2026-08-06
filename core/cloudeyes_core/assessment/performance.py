"""Performance assessment guardrails."""

from __future__ import annotations

from ..models import AssessmentDimension, AssessmentStatus, DimensionAssessment, ProviderReport


def assess_performance(report: ProviderReport) -> DimensionAssessment:
    """Refuse an absolute performance verdict without a compatible peer baseline."""

    return DimensionAssessment(
        dimension=AssessmentDimension.PERFORMANCE,
        status=AssessmentStatus.NOT_ASSESSED,
        level=None,
        rule_id="performance.compatible_peer_required.v1",
        summary=(
            "Performance was measured but not graded because no compatible peer baseline "
            "was supplied."
        ),
        evidence_refs=tuple(item.cohort_id for item in report.cohorts),
        limitations=("compatible_peer_baseline_required",),
    )
