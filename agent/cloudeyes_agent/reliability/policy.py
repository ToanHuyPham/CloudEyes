"""Deterministic quality and elapsed-time policies shared by benchmark profiles."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from cloudeyes_core.models import (
    Measurement,
    MeasurementStatus,
    SampleQuality,
    SampleQualityStatus,
)


@dataclass(frozen=True, slots=True)
class ReliabilityPolicy:
    """Rules used to classify one sample without hiding partial results.

    The timeout is intentionally a soft elapsed-time budget. It records an explicit
    warning after a measurement returns; it does not kill worker threads or leave
    partially written benchmark files behind.
    """

    max_measurement_seconds: float | None = None
    require_success: bool = True
    warn_on_failed_measurement: bool = True
    warn_on_skipped_measurement: bool = True

    def __post_init__(self) -> None:
        if self.max_measurement_seconds is not None and self.max_measurement_seconds <= 0:
            raise ValueError("max_measurement_seconds must be greater than zero")


def _duration_seconds(measurement: Measurement) -> float:
    duration: timedelta = measurement.finished_at - measurement.started_at
    return max(0.0, duration.total_seconds())


def evaluate_sample_quality(
    measurements: tuple[Measurement, ...],
    *,
    warnings: tuple[str, ...] = (),
    invalid_error: str = "no_successful_measurements",
    policy: ReliabilityPolicy | None = None,
) -> SampleQuality:
    """Return a stable quality result for a set of measurements.

    Failed and skipped measurements remain visible as warnings whenever at least one
    measurement succeeded. A sample with no successful measurement is invalid.
    """

    selected = policy or ReliabilityPolicy()
    collected = list(warnings)

    successful = tuple(item for item in measurements if item.status is MeasurementStatus.SUCCESS)
    failed = tuple(item for item in measurements if item.status is MeasurementStatus.FAILED)
    skipped = tuple(item for item in measurements if item.status is MeasurementStatus.SKIPPED)

    if selected.warn_on_failed_measurement:
        collected.extend(f"measurement_failed:{item.tool}" for item in failed)
    if selected.warn_on_skipped_measurement:
        collected.extend(f"measurement_skipped:{item.tool}" for item in skipped)

    if selected.max_measurement_seconds is not None:
        for item in measurements:
            if _duration_seconds(item) > selected.max_measurement_seconds:
                collected.append(f"measurement_duration_exceeded:{item.tool}")

    unique_warnings = tuple(dict.fromkeys(collected))
    if selected.require_success and not successful:
        return SampleQuality(
            status=SampleQualityStatus.INVALID,
            warnings=unique_warnings,
            errors=(invalid_error,),
        )
    if unique_warnings:
        return SampleQuality(
            status=SampleQualityStatus.VALID_WITH_WARNINGS,
            warnings=unique_warnings,
        )
    return SampleQuality(status=SampleQualityStatus.VALID)
