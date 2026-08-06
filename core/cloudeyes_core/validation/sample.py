"""Validation rules for complete CloudEyes samples."""

from __future__ import annotations

from dataclasses import dataclass, field

from cloudeyes_core.models import (
    MeasurementStatus,
    Sample,
    SampleQualityStatus,
)


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Result returned by sample validation."""

    valid: bool
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)


def validate_sample(sample: Sample) -> ValidationResult:
    """Validate relationships that involve multiple sample fields."""

    errors: list[str] = []
    warnings: list[str] = []

    if sample.protocol.profile not in {
        measurement.profile for measurement in sample.measurements
    }:
        errors.append(
            "sample protocol profile does not match any measurement profile"
        )

    incompatible_versions = {
        measurement.protocol_version
        for measurement in sample.measurements
        if measurement.protocol_version != sample.protocol.version
    }

    if incompatible_versions:
        errors.append(
            "measurement protocol versions do not match sample protocol version"
        )

    measurement_ids = [
        measurement.measurement_id
        for measurement in sample.measurements
    ]

    if len(measurement_ids) != len(set(measurement_ids)):
        errors.append("measurement IDs must be unique inside a sample")

    metric_names: set[str] = set()

    for measurement in sample.measurements:
        if measurement.status is MeasurementStatus.SUCCESS:
            for metric in measurement.metrics:
                metric_names.add(metric.name)

        if measurement.status is MeasurementStatus.SKIPPED:
            warnings.append(
                f"measurement skipped: {measurement.measurement_id}"
            )

        if measurement.status is MeasurementStatus.FAILED:
            warnings.append(
                f"measurement failed: {measurement.measurement_id}"
            )

    if not metric_names:
        errors.append("sample does not contain any successful metrics")

    if sample.quality.status is SampleQualityStatus.INVALID:
        errors.extend(sample.quality.errors)

    warnings.extend(sample.quality.warnings)

    return ValidationResult(
        valid=not errors,
        errors=tuple(dict.fromkeys(errors)),
        warnings=tuple(dict.fromkeys(warnings)),
    )
