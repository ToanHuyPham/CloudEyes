"""Tests for CloudEyes cohort metric aggregation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.cloudeyes_core.cohorts import (
    build_cohorts,
    summarize_cohort,
)
from core.cloudeyes_core.models import (
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
    values: tuple[float, ...],
    *,
    unit: str = "events_per_second",
) -> Sample:
    created_at = datetime.now(UTC)

    measurements = tuple(
        Measurement(
            measurement_id=f"{sample_id}-cpu-{index}",
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
                    unit=unit,
                    direction=MetricDirection.HIGHER_IS_BETTER,
                ),
            ),
        )
        for index, value in enumerate(values)
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
        measurements=measurements,
        quality=SampleQuality(
            status=SampleQualityStatus.VALID,
        ),
    )


def test_cohort_summary_uses_one_value_per_sample() -> None:
    first = make_sample(
        "sample-001",
        (100.0, 110.0, 120.0),
    )
    second = make_sample(
        "sample-002",
        (200.0,),
    )

    cohort = build_cohorts((first, second))[0]
    result = summarize_cohort(cohort)

    metric = result.metrics[0]

    assert metric.contributing_samples == 2
    assert metric.raw_observations == 4

    # Sample 1 contributes median 110.
    # Sample 2 contributes 200.
    assert metric.statistics.median == 155.0
    assert metric.statistics.mean == 155.0


def test_cohort_summary_reports_total_samples() -> None:
    cohort = build_cohorts(
        (
            make_sample("sample-001", (100.0,)),
            make_sample("sample-002", (110.0,)),
            make_sample("sample-003", (120.0,)),
        )
    )[0]

    result = summarize_cohort(cohort)

    assert result.total_samples == 3
    assert result.metrics[0].contributing_samples == 3


def test_incompatible_metric_units_are_rejected() -> None:
    first = make_sample(
        "sample-001",
        (100.0,),
        unit="events_per_second",
    )
    second = make_sample(
        "sample-002",
        (200.0,),
        unit="operations_per_second",
    )

    cohort = build_cohorts((first, second))[0]

    with pytest.raises(ValueError, match="incompatible units"):
        summarize_cohort(cohort)


def test_metric_summaries_are_sorted_by_name() -> None:
    sample = make_sample("sample-001", (100.0,))
    cohort = build_cohorts((sample,))[0]

    result = summarize_cohort(cohort)

    names = tuple(metric.name for metric in result.metrics)

    assert names == tuple(sorted(names))
