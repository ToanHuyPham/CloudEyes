"""Reliability assessment from measurement completion and sample quality."""

from __future__ import annotations

from ..models import (
    AssessmentDimension,
    AssessmentStatus,
    Cohort,
    ConfidenceLevel,
    DimensionAssessment,
    MeasurementStatus,
    SampleQualityStatus,
)


def successful_measurement_ratio(cohorts: tuple[Cohort, ...]) -> float:
    """Return successful measurements divided by all observed measurements."""

    statuses = [
        measurement.status
        for cohort in cohorts
        for sample in cohort.samples
        for measurement in sample.measurements
    ]
    if not statuses:
        return 0.0
    successes = sum(status is MeasurementStatus.SUCCESS for status in statuses)
    return successes / len(statuses)


def assess_reliability(cohorts: tuple[Cohort, ...]) -> DimensionAssessment:
    """Assess collection reliability without inferring provider uptime."""

    ratio = successful_measurement_ratio(cohorts)
    samples = tuple(sample for cohort in cohorts for sample in cohort.samples)
    warning_count = sum(
        sample.quality.status is SampleQualityStatus.VALID_WITH_WARNINGS for sample in samples
    )
    error_count = sum(len(sample.quality.errors) for sample in samples)

    if ratio >= 0.95 and warning_count == 0 and error_count == 0:
        level = ConfidenceLevel.HIGH
        summary = (
            f"Measurement completion was high at {ratio:.1%}, with no sample warnings or errors."
        )
    elif ratio >= 0.80 and error_count == 0:
        level = ConfidenceLevel.MEDIUM
        summary = (
            f"Measurement completion was {ratio:.1%}; some samples contained quality warnings."
        )
    else:
        level = ConfidenceLevel.LOW
        summary = (
            f"Measurement completion was {ratio:.1%}; failed or invalid evidence limits "
            "reliability."
        )

    limitations: list[str] = []
    if warning_count:
        limitations.append(f"samples_with_warnings:{warning_count}")
    if error_count:
        limitations.append(f"sample_errors:{error_count}")
    if ratio < 1.0:
        limitations.append(f"measurement_success_ratio:{ratio:.6f}")

    return DimensionAssessment(
        dimension=AssessmentDimension.RELIABILITY,
        status=AssessmentStatus.ASSESSED,
        level=level,
        rule_id="reliability.measurement_completion.v1",
        summary=summary,
        evidence_refs=tuple(sample.sample_id for sample in samples),
        limitations=tuple(limitations),
    )
