"""JSON serialization and sample deserialization."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from ..models import (
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


def to_primitive(value: Any) -> Any:
    """Convert dataclasses and enums into JSON-compatible values."""

    if is_dataclass(value) and not isinstance(value, type):
        return {key: to_primitive(item) for key, item in asdict(value).items()}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple | list):
        return [to_primitive(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): to_primitive(item) for key, item in value.items()}
    return value


def dumps(value: Any, *, indent: int = 2) -> str:
    """Serialize a CloudEyes object to deterministic JSON text."""

    return json.dumps(
        to_primitive(value),
        indent=indent,
        ensure_ascii=False,
        sort_keys=True,
        allow_nan=False,
    )


def dump(value: Any, path: str | Path, *, indent: int = 2) -> Path:
    """Serialize a CloudEyes object into a UTF-8 JSON file."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(dumps(value, indent=indent) + "\n", encoding="utf-8")
    return output_path


def _mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be an object")
    return value


def _sequence(value: Any, field_name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be an array")
    return value


def _datetime(value: Any, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a date-time string")
    try:
        result = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field_name} is not a valid ISO date-time") from error
    if result.tzinfo is None:
        raise ValueError(f"{field_name} must contain timezone information")
    return result


def sample_from_dict(data: Mapping[str, Any]) -> Sample:
    """Create a validated model graph from a sample dictionary."""

    provider_data = _mapping(data.get("provider"), "provider")
    product_data = _mapping(data.get("product"), "product")
    machine_data = _mapping(data.get("machine"), "machine")
    protocol_data = _mapping(data.get("protocol"), "protocol")
    quality_data = _mapping(data.get("quality"), "quality")
    measurements_data = _sequence(data.get("measurements"), "measurements")

    measurements: list[Measurement] = []
    for index, raw_measurement in enumerate(measurements_data):
        measurement_data = _mapping(raw_measurement, f"measurements[{index}]")
        metrics_data = _sequence(measurement_data.get("metrics"), f"measurements[{index}].metrics")
        metrics = tuple(
            Metric(
                name=_mapping(raw_metric, "metric")["name"],
                value=_mapping(raw_metric, "metric")["value"],
                unit=_mapping(raw_metric, "metric")["unit"],
                direction=MetricDirection(_mapping(raw_metric, "metric")["direction"]),
            )
            for raw_metric in metrics_data
        )
        measurements.append(
            Measurement(
                measurement_id=measurement_data["measurement_id"],
                tool=measurement_data["tool"],
                tool_version=measurement_data.get("tool_version"),
                profile=measurement_data["profile"],
                protocol_version=measurement_data["protocol_version"],
                started_at=_datetime(measurement_data["started_at"], "started_at"),
                finished_at=_datetime(measurement_data["finished_at"], "finished_at"),
                status=MeasurementStatus(measurement_data["status"]),
                metrics=metrics,
                raw_output_path=measurement_data.get("raw_output_path"),
                error=measurement_data.get("error"),
            )
        )

    return Sample(
        sample_id=data["sample_id"],
        created_at=_datetime(data["created_at"], "created_at"),
        provider=ProviderIdentity(
            provider_id=provider_data["provider_id"],
            name=provider_data["name"],
            country_code=provider_data.get("country_code"),
        ),
        product=ProductIdentity(
            product=product_data.get("product"),
            plan=product_data.get("plan"),
            region=product_data.get("region"),
            zone=product_data.get("zone"),
        ),
        machine=MachineIdentity(
            machine_type=machine_data["machine_type"],
            cpu_count=machine_data["cpu_count"],
            memory_bytes=machine_data["memory_bytes"],
            architecture=machine_data["architecture"],
        ),
        protocol=ProtocolIdentity(
            profile=protocol_data["profile"],
            version=protocol_data["version"],
            fingerprint=protocol_data["fingerprint"],
        ),
        measurements=tuple(measurements),
        quality=SampleQuality(
            status=SampleQualityStatus(quality_data["status"]),
            warnings=tuple(quality_data.get("warnings", [])),
            errors=tuple(quality_data.get("errors", [])),
        ),
    )


def loads_sample(text: str) -> Sample:
    """Deserialize one sample from JSON text."""

    data = json.loads(text)
    return sample_from_dict(_mapping(data, "sample"))


def load_sample(path: str | Path) -> Sample:
    """Deserialize one sample from a UTF-8 JSON file."""

    return loads_sample(Path(path).read_text(encoding="utf-8"))
