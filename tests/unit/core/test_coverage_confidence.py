"""Tests for coverage and confidence calculation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.cloudeyes_core.assessment import calculate_confidence
from core.cloudeyes_core.cohorts import build_cohorts, summarize_cohort
from core.cloudeyes_core.coverage import calculate_coverage
from core.cloudeyes_core.models import (
    ConfidenceLevel,
    MachineIdentity,
    Measurement,
    MeasurementStatus,
    Metric,
    MetricDirection,
    ProductIdentity,
    ProtocolIdentity,
    ProviderIdentity,
    Sample,
    SampleQuality,
    SampleQualityStatus,
)


def make_sample(
    sample_id: str,
    *,
    created_at: datetime,
    value: float,
) -> Sample:
    measurement = Measurement(
        measurement_id=f"{sample_id}-cpu",
        tool="sysbench",
        tool_version="1.0.20",
        profile="general",
        protocol_version="1.0.0",
        started_at=created_at,
        finished_at=created_at + timedelta(seconds=10),
        status=MeasurementStatus.SUCCESS,
        metrics=(
            Metric(
                name="compute.cpu.events_per_second",
                value=value,
                unit="events_per_second",
                direction=MetricDirection.HIGHER_IS_BETTER,
            ),
        ),
    )

    return Sample(
        sample_id=sample_id,
        created_at=created_at,
        provider=ProviderIdentity(
            provider_id="viettel-cloud",
            name="Viettel Cloud",
            country_code="VN",
        ),
        product=ProductIdentity(
            product="Cloud Server",
            plan="2-vcpu-4gb",
            region="hanoi",
            zone="zone-1",
        ),
        machine=MachineIdentity(
            machine_type="virtual_machine",
            cpu_count=2,
            memory_bytes=4_294_967_296,
            architecture="x86_64",
        ),
        protocol=ProtocolIdentity(
            profile="general",
            version="1.0.0",
            fingerprint="abc123",
        ),
        measurements=(measurement,),
        quality=SampleQuality(
            status=SampleQualityStatus.VALID,
        ),
    )


def make_cohort(
    count: int,
    *,
    day_span: int,
    values: tuple[float, ...] | None = None,
):
    start = datetime(2026, 8, 1, tzinfo=UTC)

    if values is None:
        values = tuple(100.0 + index for index in range(count))

    samples = tuple(
        make_sample(
            f"sample-{index}",
            created_at=start
            + timedelta(
                days=min(index, day_span - 1),
            ),
            value=values[index],
        )
        for index in range(count)
    )

    return build_cohorts(samples)[0]


def test_coverage_detects_missing_metrics() -> None:
    cohort = make_cohort(3, day_span=3)
    summary = summarize_cohort(cohort)

    coverage = calculate_coverage(
        cohort,
        summary,
        expected_metrics=(
            "compute.cpu.events_per_second",
            "memory.bandwidth.bytes_per_second",
        ),
    )

    assert coverage.metric_ratio == 0.5
    assert (
        "missing_metric:memory.bandwidth.bytes_per_second"
        in coverage.gaps
    )


def test_small_cohort_has_low_statistical_confidence() -> None:
    cohort = make_cohort(2, day_span=1)
    summary = summarize_cohort(cohort)
    coverage = calculate_coverage(
        cohort,
        summary,
        expected_metrics=(
            "compute.cpu.events_per_second",
        ),
    )

    confidence = calculate_confidence(summary, coverage)

    assert confidence.statistical is ConfidenceLevel.LOW
    assert confidence.overall is ConfidenceLevel.LOW


def test_medium_sample_set_has_medium_statistical_confidence() -> None:
    cohort = make_cohort(3, day_span=3)
    summary = summarize_cohort(cohort)
    coverage = calculate_coverage(
        cohort,
        summary,
        expected_metrics=(
            "compute.cpu.events_per_second",
        ),
    )

    confidence = calculate_confidence(summary, coverage)

    assert confidence.statistical is ConfidenceLevel.MEDIUM


def test_stable_metrics_have_high_measurement_confidence() -> None:
    cohort = make_cohort(
        3,
        day_span=3,
        values=(100.0, 101.0, 99.0),
    )

    summary = summarize_cohort(cohort)
    coverage = calculate_coverage(
        cohort,
        summary,
        expected_metrics=(
            "compute.cpu.events_per_second",
        ),
    )

    confidence = calculate_confidence(summary, coverage)

    assert confidence.measurement is ConfidenceLevel.HIGH


def test_unstable_metrics_have_low_measurement_confidence() -> None:
    cohort = make_cohort(
        3,
        day_span=3,
        values=(50.0, 100.0, 200.0),
    )

    summary = summarize_cohort(cohort)
    coverage = calculate_coverage(
        cohort,
        summary,
        expected_metrics=(
            "compute.cpu.events_per_second",
        ),
    )

    confidence = calculate_confidence(summary, coverage)

    assert confidence.measurement is ConfidenceLevel.LOW


def test_complete_metric_coverage_can_be_high() -> None:
    cohort = make_cohort(10, day_span=7)
    summary = summarize_cohort(cohort)
    coverage = calculate_coverage(
        cohort,
        summary,
        expected_metrics=(
            "compute.cpu.events_per_second",
        ),
    )

    confidence = calculate_confidence(summary, coverage)

    assert confidence.coverage is ConfidenceLevel.HIGH
    assert confidence.statistical is ConfidenceLevel.HIGH
