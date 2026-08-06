"""Consistency assessment from cohort metric dispersion."""

from __future__ import annotations

from ..models import (
    AssessmentDimension,
    AssessmentStatus,
    ConfidenceLevel,
    DimensionAssessment,
    ProviderReport,
)


def assess_consistency(report: ProviderReport) -> DimensionAssessment:
    """Assess the worst observed coefficient of variation across cohort metrics."""

    observations: list[tuple[float, str, str]] = []
    missing: list[str] = []
    for cohort in report.cohorts:
        for metric in cohort.metrics:
            coefficient = metric.statistics.coefficient_of_variation
            ref = f"{cohort.cohort_id}:{metric.name}"
            if metric.contributing_samples < 2 or coefficient is None:
                missing.append(ref)
            else:
                observations.append((coefficient, cohort.cohort_id, metric.name))

    if not observations:
        return DimensionAssessment(
            dimension=AssessmentDimension.CONSISTENCY,
            status=AssessmentStatus.ASSESSED,
            level=ConfidenceLevel.LOW,
            rule_id="consistency.cv.v1",
            summary="No metric had enough finite variation data for a stable consistency result.",
            evidence_refs=tuple(item.cohort_id for item in report.cohorts),
            limitations=("coefficient_of_variation_unavailable",),
        )

    worst, cohort_id, metric_name = max(observations, key=lambda item: item[0])
    if worst <= 0.10:
        level = ConfidenceLevel.HIGH
        summary = f"Observed metrics were stable; worst coefficient of variation was {worst:.3f}."
    elif worst <= 0.25:
        level = ConfidenceLevel.MEDIUM
        summary = f"Observed metrics had moderate variation; worst coefficient was {worst:.3f}."
    else:
        level = ConfidenceLevel.LOW
        summary = f"Observed metrics were variable; worst coefficient of variation was {worst:.3f}."

    limitations = tuple(f"variation_unavailable:{item}" for item in sorted(missing))
    return DimensionAssessment(
        dimension=AssessmentDimension.CONSISTENCY,
        status=AssessmentStatus.ASSESSED,
        level=level,
        rule_id="consistency.cv.v1",
        summary=summary,
        evidence_refs=(f"{cohort_id}:{metric_name}",),
        limitations=limitations,
    )
