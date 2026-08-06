"""Tests for sample validation and JSON serialization."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

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
from core.cloudeyes_core.serialization import dump, dumps
from core.cloudeyes_core.validation import validate_sample


def make_sample() -> Sample:
    started_at = datetime.now(UTC)

    measurement = Measurement(
        measurement_id="cpu-001",
        tool="sysbench",
        tool_version="1.0.20",
        profile="general",
        protocol_version="1.0.0",
        started_at=started_at,
        finished_at=started_at + timedelta(seconds=10),
        status=MeasurementStatus.SUCCESS,
        metrics=(
            Metric(
                name="compute.cpu.events_per_second",
                value=1250,
                unit="events_per_second",
                direction=MetricDirection.HIGHER_IS_BETTER,
            ),
        ),
        raw_output_path="raw/sysbench-cpu.json",
    )

    return Sample.create(
        sample_id="sample-001",
        provider=ProviderIdentity(
            provider_id="viettel-cloud",
            name="Viettel Cloud",
            country_code="VN",
        ),
        product=ProductIdentity(
            product="Cloud Server",
            plan="2 vCPU / 4 GB",
            region="Hanoi",
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


def test_sample_validation_passes() -> None:
    result = validate_sample(make_sample())

    assert result.valid is True
    assert result.errors == ()


def test_sample_serializes_to_json() -> None:
    data = json.loads(dumps(make_sample()))

    assert data["sample_id"] == "sample-001"
    assert data["provider"]["provider_id"] == "viettel-cloud"
    assert data["quality"]["status"] == "valid"
    assert data["measurements"][0]["status"] == "success"


def test_sample_can_be_written_to_file(tmp_path) -> None:
    output_path = dump(
        make_sample(),
        tmp_path / "sample.json",
    )

    assert output_path.exists()

    data = json.loads(output_path.read_text(encoding="utf-8"))

    assert data["protocol"]["version"] == "1.0.0"
    assert data["machine"]["cpu_count"] == 2
