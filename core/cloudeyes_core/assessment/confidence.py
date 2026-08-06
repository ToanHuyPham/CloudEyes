"""Confidence calculation for CloudEyes assessments."""

from __future__ import annotations

from cloudeyes_core.cohorts import CohortSummary
from cloudeyes_core.models import (
    Confidence,
    ConfidenceLevel,
    Coverage,
)


def _measurement_confidence(summary: CohortSummary) -> ConfidenceLevel:
    """Evaluate whether metrics are sufficiently stable."""

    if not summary.metrics:
        return ConfidenceLevel.LOW

    coefficients = [
        metric.statistics.coefficient_of_variation
        for metric in summary.metrics
        if metric.statistics.coefficient_of_variation is not None
    ]

    if not coefficients:
        return ConfidenceLevel.LOW

    worst = max(coefficients)

    if worst <= 0.10:
        return ConfidenceLevel.HIGH

    if worst <= 0.25:
        return ConfidenceLevel.MEDIUM

    return ConfidenceLevel.LOW


def _statistical_confidence(coverage: Coverage) -> ConfidenceLevel:
    """Evaluate sample count and observation duration."""

    if coverage.sample_count >= 10 and coverage.observation_days >= 7:
        return ConfidenceLevel.HIGH

    if coverage.sample_count >= 3 and coverage.observation_days >= 3:
        return ConfidenceLevel.MEDIUM

    return ConfidenceLevel.LOW


def _coverage_confidence(coverage: Coverage) -> ConfidenceLevel:
    """Evaluate coverage of expected evidence."""

    ratio = coverage.metric_ratio

    if ratio >= 0.90 and coverage.regions and coverage.plans:
        return ConfidenceLevel.HIGH

    if ratio >= 0.60:
        return ConfidenceLevel.MEDIUM

    return ConfidenceLevel.LOW


def calculate_confidence(
    summary: CohortSummary,
    coverage: Coverage,
) -> Confidence:
    """Calculate confidence dimensions for one cohort assessment."""

    return Confidence(
        measurement=_measurement_confidence(summary),
        statistical=_statistical_confidence(coverage),
        coverage=_coverage_confidence(coverage),
    )
