"""End-to-end execution of the CloudEyes Networking Profile v1."""

from __future__ import annotations

import platform
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from cloudeyes_core.models import (
    MachineIdentity,
    Measurement,
    MeasurementStatus,
    ProductIdentity,
    ProtocolIdentity,
    ProviderIdentity,
    Sample,
    SampleQuality,
    SampleQualityStatus,
)

from ...discovery import DiscoveryResult, VirtualizationKind, discover_all
from ...storage import write_raw_output
from .benchmarks import NetworkingBenchmarkResult, benchmark_networking_profile
from .config import NetworkingProfileConfig

Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _provider_identity(
    discovery: DiscoveryResult,
    *,
    provider_id: str | None,
    provider_name: str | None,
    country_code: str | None,
) -> ProviderIdentity:
    resolved_id = provider_id or discovery.provider.provider_id or "unknown"
    resolved_name = provider_name or discovery.provider.provider_name or "Unknown Provider"
    return ProviderIdentity(resolved_id, resolved_name, country_code)


def _machine_identity(discovery: DiscoveryResult) -> MachineIdentity:
    machine_type = discovery.virtualization.kind.value
    if discovery.virtualization.kind is VirtualizationKind.UNKNOWN:
        machine_type = "unknown"
    return MachineIdentity(
        machine_type=machine_type,
        cpu_count=discovery.hardware.logical_cpu_count,
        memory_bytes=discovery.hardware.memory_bytes or 1,
        architecture=discovery.hardware.architecture,
    )


def _measurement(
    *,
    sample_id: str,
    config: NetworkingProfileConfig,
    raw_output_dir: str | Path | None,
    clock: Clock,
) -> tuple[Measurement, tuple[str, ...]]:
    started_at = clock()
    try:
        result: NetworkingBenchmarkResult = benchmark_networking_profile(config=config)
        raw_output_path: str | None = None
        if raw_output_dir is not None:
            payload = dict(result.evidence)
            payload["sample_id"] = sample_id
            path = write_raw_output(
                payload,
                directory=raw_output_dir,
                stem=f"{sample_id}-networking",
            )
            raw_output_path = path.as_posix()
        measurement = Measurement(
            measurement_id=f"{sample_id}-networking",
            tool="python-networking-profile",
            tool_version=platform.python_version(),
            profile="networking",
            protocol_version=config.version,
            started_at=started_at,
            finished_at=clock(),
            status=MeasurementStatus.SUCCESS,
            metrics=result.metrics,
            raw_output_path=raw_output_path,
        )
        return measurement, result.warnings
    except Exception as error:  # pragma: no cover - tested through monkeypatch
        measurement = Measurement(
            measurement_id=f"{sample_id}-networking",
            tool="python-networking-profile",
            tool_version=platform.python_version(),
            profile="networking",
            protocol_version=config.version,
            started_at=started_at,
            finished_at=clock(),
            status=MeasurementStatus.FAILED,
            error=f"{type(error).__name__}: networking benchmark failed",
        )
        return measurement, ()


def run_networking_profile(
    *,
    config: NetworkingProfileConfig | None = None,
    discovery: DiscoveryResult | None = None,
    sample_id: str | None = None,
    raw_output_dir: str | Path | None = None,
    provider_id: str | None = None,
    provider_name: str | None = None,
    country_code: str | None = None,
    product: str | None = None,
    plan: str | None = None,
    region: str | None = None,
    zone: str | None = None,
    clock: Clock = _utc_now,
) -> Sample:
    """Discover the host, benchmark one endpoint, and build one Core sample."""

    selected_config = config or NetworkingProfileConfig()
    discovered = discovery or discover_all()
    resolved_sample_id = sample_id or f"networking-{uuid.uuid4().hex}"
    measurement, benchmark_warnings = _measurement(
        sample_id=resolved_sample_id,
        config=selected_config,
        raw_output_dir=raw_output_dir,
        clock=clock,
    )

    warnings = [*discovered.warnings, *benchmark_warnings]
    errors: tuple[str, ...] = ()
    if discovered.provider.provider_id is None and provider_id is None:
        warnings.append("provider_unknown")
    if discovered.hardware.memory_bytes is None:
        warnings.append("memory_capacity_unknown")
    if raw_output_dir is None:
        warnings.append("raw_output_not_persisted")

    if measurement.status is MeasurementStatus.FAILED:
        quality_status = SampleQualityStatus.INVALID
        errors = ("networking_measurement_failed",)
    elif warnings:
        quality_status = SampleQualityStatus.VALID_WITH_WARNINGS
    else:
        quality_status = SampleQualityStatus.VALID

    return Sample(
        sample_id=resolved_sample_id,
        created_at=clock(),
        provider=_provider_identity(
            discovered,
            provider_id=provider_id,
            provider_name=provider_name,
            country_code=country_code,
        ),
        product=ProductIdentity(product, plan, region, zone),
        machine=_machine_identity(discovered),
        protocol=ProtocolIdentity(
            profile="networking",
            version=selected_config.version,
            fingerprint=selected_config.fingerprint,
        ),
        measurements=(measurement,),
        quality=SampleQuality(
            status=quality_status,
            warnings=tuple(dict.fromkeys(warnings)),
            errors=errors,
        ),
    )
