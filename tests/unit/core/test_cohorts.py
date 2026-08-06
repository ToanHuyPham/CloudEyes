"""Tests for CloudEyes cohort grouping."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.cloudeyes_core.cohorts import (
    build_cohort_key,
    build_cohorts,
    compare_samples,
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
    *,
    provider_id: str = "viettel-cloud",
    region: str = "hanoi",
    plan: str = "2-vcpu-4gb",
    fingerprint: str = "abc123",
    created_offset: int = 0,
) -> Sample:
    created_at = datetime.now(UTC) + timedelta(minutes=created_offset)

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
                value=1250,
                unit="events_per_second",
                direction=MetricDirection.HIGHER_IS_BETTER,
            ),
        ),
    )

    return Sample(
        sample_id=sample_id,
        created_at=created_at,
        provider=ProviderIdentity(
            provider_id=provider_id,
            name="Example Provider",
            country_code="VN",
        ),
        product=ProductIdentity(
            product="Cloud Server",
            plan=plan,
            region=region,
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
            fingerprint=fingerprint,
        ),
        measurements=(measurement,),
        quality=SampleQuality(
            status=SampleQualityStatus.VALID,
        ),
    )


def test_same_samples_have_same_cohort_key() -> None:
    first = make_sample("sample-001")
    second = make_sample("sample-002")

    assert build_cohort_key(first) == build_cohort_key(second)


def test_different_regions_are_not_compatible() -> None:
    first = make_sample("sample-001", region="hanoi")
    second = make_sample("sample-002", region="hochiminh")

    result = compare_samples(first, second)

    assert result.compatible is False
    assert "region" in result.differences


def test_different_protocol_fingerprints_are_not_compatible() -> None:
    first = make_sample("sample-001", fingerprint="abc123")
    second = make_sample("sample-002", fingerprint="xyz999")

    result = compare_samples(first, second)

    assert result.compatible is False
    assert "protocol_fingerprint" in result.differences


def test_compatible_samples_are_grouped() -> None:
    samples = (
        make_sample("sample-002", created_offset=10),
        make_sample("sample-001", created_offset=0),
    )

    cohorts = build_cohorts(samples)

    assert len(cohorts) == 1
    assert cohorts[0].sample_count == 2
    assert cohorts[0].samples[0].sample_id == "sample-001"
    assert cohorts[0].samples[1].sample_id == "sample-002"


def test_incompatible_samples_create_separate_cohorts() -> None:
    samples = (
        make_sample("sample-001", region="hanoi"),
        make_sample("sample-002", region="hochiminh"),
        make_sample("sample-003", plan="4-vcpu-8gb"),
    )

    cohorts = build_cohorts(samples)

    assert len(cohorts) == 3


def test_empty_input_returns_no_cohorts() -> None:
    assert build_cohorts(()) == ()
