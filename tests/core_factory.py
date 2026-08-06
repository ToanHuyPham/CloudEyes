"""Reusable factories for Core Foundation tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from cloudeyes_core.models import (
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
    sample_id: str = "sample-001",
    *,
    created_at: datetime | None = None,
    provider_id: str = "viettel-cloud",
    provider_name: str = "Viettel Cloud",
    country_code: str = "VN",
    plan: str = "2-vcpu-4gb",
    region: str = "hanoi",
    zone: str = "zone-1",
    cpu_count: int = 2,
    memory_bytes: int = 4_294_967_296,
    profile: str = "general",
    protocol_version: str = "1.0.0",
    fingerprint: str = "abc123",
    values: tuple[float, ...] = (100.0,),
    unit: str = "events_per_second",
    metric_name: str = "compute.cpu.events_per_second",
    quality_status: SampleQualityStatus = SampleQualityStatus.VALID,
    quality_errors: tuple[str, ...] = (),
) -> Sample:
    created = created_at or datetime(2026, 8, 1, tzinfo=UTC)
    measurements = tuple(
        Measurement(
            measurement_id=f"{sample_id}-cpu-{index}",
            tool="sysbench",
            tool_version="1.0.20",
            profile=profile,
            protocol_version=protocol_version,
            started_at=created + timedelta(seconds=index * 20),
            finished_at=created + timedelta(seconds=index * 20 + 10),
            status=MeasurementStatus.SUCCESS,
            metrics=(
                Metric(
                    name=metric_name,
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
        created_at=created,
        provider=ProviderIdentity(provider_id, provider_name, country_code),
        product=ProductIdentity("Cloud Server", plan, region, zone),
        machine=MachineIdentity("virtual_machine", cpu_count, memory_bytes, "x86_64"),
        protocol=ProtocolIdentity(profile, protocol_version, fingerprint),
        measurements=measurements,
        quality=SampleQuality(quality_status, errors=quality_errors),
    )
