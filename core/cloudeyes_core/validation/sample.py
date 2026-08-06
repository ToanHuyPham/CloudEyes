"""Cross-field validation rules for complete samples."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..models import MeasurementStatus, Sample, SampleQualityStatus


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Result returned by sample validation."""

    valid: bool
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)


class SampleValidationError(ValueError):
    """Raised when a sample cannot be safely accepted."""

    def __init__(self, errors: tuple[str, ...]):
        self.errors = errors
        super().__init__("; ".join(errors))


def validate_sample(sample: Sample) -> ValidationResult:
    """Validate relationships that involve multiple sample fields."""

    errors: list[str] = []
    warnings: list[str] = []

    measurement_ids = [measurement.measurement_id for measurement in sample.measurements]

    if len(measurement_ids) != len(set(measurement_ids)):
        errors.append("measurement IDs must be unique inside a sample")

    metric_contracts: dict[str, tuple[str, object]] = {}
    successful_metric_count = 0

    for measurement in sample.measurements:
        if measurement.profile != sample.protocol.profile:
            errors.append(
                f"measurement {measurement.measurement_id} profile does not match sample protocol"
            )

        if measurement.protocol_version != sample.protocol.version:
            errors.append(
                f"measurement {measurement.measurement_id} "
                "protocol version does not match sample protocol"
            )

        metric_names = [metric.name for metric in measurement.metrics]

        if len(metric_names) != len(set(metric_names)):
            errors.append(
                f"measurement {measurement.measurement_id} contains duplicate metric names"
            )

        if measurement.status is MeasurementStatus.SUCCESS:
            successful_metric_count += len(measurement.metrics)

            for metric in measurement.metrics:
                contract = (metric.unit, metric.direction)
                existing = metric_contracts.setdefault(
                    metric.name,
                    contract,
                )

                if existing != contract:
                    errors.append(f"metric {metric.name} uses incompatible unit or direction")

        elif measurement.status is MeasurementStatus.FAILED:
            warnings.append(f"measurement failed: {measurement.measurement_id}")

        elif measurement.status is MeasurementStatus.SKIPPED:
            warnings.append(f"measurement skipped: {measurement.measurement_id}")

    if successful_metric_count == 0:
        errors.append("sample does not contain any successful metrics")

    if sample.quality.status is SampleQualityStatus.INVALID:
        errors.extend(sample.quality.errors)

    warnings.extend(sample.quality.warnings)

    unique_errors = tuple(dict.fromkeys(errors))
    unique_warnings = tuple(dict.fromkeys(warnings))

    return ValidationResult(
        valid=not unique_errors,
        errors=unique_errors,
        warnings=unique_warnings,
    )


def ensure_valid_sample(sample: Sample) -> None:
    """Raise SampleValidationError unless a sample is valid."""

    result = validate_sample(sample)

    if not result.valid:
        raise SampleValidationError(result.errors)
