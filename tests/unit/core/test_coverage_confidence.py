"""Tests for coverage and confidence calculation."""

from datetime import UTC, datetime, timedelta

from cloudeyes_core.assessment import calculate_confidence
from cloudeyes_core.cohorts import build_cohorts, summarize_cohort
from cloudeyes_core.coverage import calculate_coverage
from cloudeyes_core.models import ConfidenceLevel
from tests.core_factory import make_sample


def _cohort(count: int, days: int, values: tuple[float, ...]):
    start = datetime(2026, 8, 1, tzinfo=UTC)
    samples = tuple(
        make_sample(
            f"sample-{index}",
            created_at=start + timedelta(days=min(index, days - 1)),
            values=(values[index],),
        )
        for index in range(count)
    )
    return build_cohorts(samples)[0]


def test_missing_metric_is_explicit_gap() -> None:
    cohort = _cohort(3, 3, (100.0, 101.0, 99.0))
    summary = summarize_cohort(cohort)
    coverage = calculate_coverage(cohort, summary, expected_metrics=("compute.cpu.events_per_second", "memory.bandwidth"))
    assert coverage.metric_ratio == 0.5
    assert "missing_metric:memory.bandwidth" in coverage.gaps


def test_small_cohort_has_low_statistical_confidence() -> None:
    cohort = _cohort(2, 1, (100.0, 101.0))
    summary = summarize_cohort(cohort)
    confidence = calculate_confidence(summary, calculate_coverage(cohort, summary))
    assert confidence.statistical is ConfidenceLevel.LOW


def test_stable_metrics_have_high_measurement_confidence() -> None:
    cohort = _cohort(3, 3, (100.0, 101.0, 99.0))
    summary = summarize_cohort(cohort)
    confidence = calculate_confidence(summary, calculate_coverage(cohort, summary))
    assert confidence.measurement is ConfidenceLevel.HIGH


def test_unstable_metrics_have_low_measurement_confidence() -> None:
    cohort = _cohort(3, 3, (50.0, 100.0, 200.0))
    summary = summarize_cohort(cohort)
    confidence = calculate_confidence(summary, calculate_coverage(cohort, summary))
    assert confidence.measurement is ConfidenceLevel.LOW


def test_large_complete_cohort_has_high_statistical_confidence() -> None:
    cohort = _cohort(10, 7, tuple(100.0 + index for index in range(10)))
    summary = summarize_cohort(cohort)
    coverage = calculate_coverage(cohort, summary, expected_metrics=("compute.cpu.events_per_second",))
    confidence = calculate_confidence(summary, coverage)
    assert confidence.statistical is ConfidenceLevel.HIGH
    assert confidence.coverage is ConfidenceLevel.HIGH
