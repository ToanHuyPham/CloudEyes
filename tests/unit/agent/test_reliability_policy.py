"""Tests for shared measurement reliability policies."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from cloudeyes_agent.reliability import ReliabilityPolicy, evaluate_sample_quality
from cloudeyes_core.models import (
    Measurement,
    MeasurementStatus,
    Metric,
    SampleQualityStatus,
)


def make_measurement(
    status: MeasurementStatus,
    *,
    tool: str = "test-tool",
    duration_seconds: float = 1.0,
) -> Measurement:
    started = datetime(2026, 1, 1, tzinfo=UTC)
    return Measurement(
        measurement_id=f"measurement-{tool}",
        tool=tool,
        tool_version="1.0",
        profile="test",
        protocol_version="1.0.0",
        started_at=started,
        finished_at=started + timedelta(seconds=duration_seconds),
        status=status,
        metrics=(Metric("test.metric", 1.0, "count"),)
        if status is MeasurementStatus.SUCCESS
        else (),
        error="failed" if status is MeasurementStatus.FAILED else None,
    )


def test_valid_when_measurement_succeeds() -> None:
    quality = evaluate_sample_quality((make_measurement(MeasurementStatus.SUCCESS),))
    assert quality.status is SampleQualityStatus.VALID
    assert quality.warnings == ()
    assert quality.errors == ()


def test_partial_failure_is_warning_when_another_measurement_succeeds() -> None:
    quality = evaluate_sample_quality(
        (
            make_measurement(MeasurementStatus.SUCCESS, tool="cpu"),
            make_measurement(MeasurementStatus.FAILED, tool="storage"),
        )
    )
    assert quality.status is SampleQualityStatus.VALID_WITH_WARNINGS
    assert quality.warnings == ("measurement_failed:storage",)


def test_no_successful_measurement_is_invalid() -> None:
    quality = evaluate_sample_quality(
        (make_measurement(MeasurementStatus.FAILED),),
        invalid_error="compute_measurement_failed",
    )
    assert quality.status is SampleQualityStatus.INVALID
    assert quality.errors == ("compute_measurement_failed",)


def test_elapsed_budget_adds_stable_warning() -> None:
    quality = evaluate_sample_quality(
        (make_measurement(MeasurementStatus.SUCCESS, duration_seconds=10),),
        policy=ReliabilityPolicy(max_measurement_seconds=5),
    )
    assert quality.status is SampleQualityStatus.VALID_WITH_WARNINGS
    assert quality.warnings == ("measurement_duration_exceeded:test-tool",)


def test_duplicate_warnings_are_removed_without_reordering() -> None:
    quality = evaluate_sample_quality(
        (make_measurement(MeasurementStatus.SUCCESS),),
        warnings=("provider_unknown", "provider_unknown", "custom"),
    )
    assert quality.warnings == ("provider_unknown", "custom")


def test_timeout_budget_must_be_positive() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        ReliabilityPolicy(max_measurement_seconds=0)
