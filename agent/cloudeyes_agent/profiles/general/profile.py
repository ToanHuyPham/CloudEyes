"""End-to-end execution of the CloudEyes General Profile v1."""

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
    Metric,
    ProductIdentity,
    ProtocolIdentity,
    ProviderIdentity,
    Sample,
    SampleQuality,
    SampleQualityStatus,
)

from ...discovery import DiscoveryResult, VirtualizationKind, discover_all
from .benchmarks import benchmark_cpu, benchmark_memory, benchmark_storage
from .config import GeneralProfileConfig

Benchmark = Callable[[], tuple[Metric, ...]]
Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _measurement(
    *,
    measurement_id: str,
    tool: str,
    protocol_version: str,
    benchmark: Benchmark,
    clock: Clock,
) -> Measurement:
    started_at = clock()
    try:
        metrics = tuple(benchmark())
    except Exception as error:  # pragma: no cover - tested through injected failure
        return Measurement(
            measurement_id=measurement_id,
            tool=tool,
            tool_version=platform.python_version(),
            profile="general",
            protocol_version=protocol_version,
            started_at=started_at,
            finished_at=clock(),
            status=MeasurementStatus.FAILED,
            error=f"{type(error).__name__}: benchmark failed",
        )

    return Measurement(
        measurement_id=measurement_id,
        tool=tool,
        tool_version=platform.python_version(),
        profile="general",
        protocol_version=protocol_version,
        started_at=started_at,
        finished_at=clock(),
        status=MeasurementStatus.SUCCESS,
        metrics=metrics,
    )


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


def run_general_profile(
    *,
    config: GeneralProfileConfig | None = None,
    discovery: DiscoveryResult | None = None,
    sample_id: str | None = None,
    work_dir: str | Path | None = None,
    provider_id: str | None = None,
    provider_name: str | None = None,
    country_code: str | None = None,
    product: str | None = None,
    plan: str | None = None,
    region: str | None = None,
    zone: str | None = None,
    clock: Clock = _utc_now,
) -> Sample:
    """Discover the machine, run bounded benchmarks, and build one sample."""

    selected_config = config or GeneralProfileConfig()
    discovered = discovery or discover_all()
    resolved_sample_id = sample_id or f"general-{uuid.uuid4().hex}"

    measurements = [
        _measurement(
            measurement_id=f"{resolved_sample_id}-cpu",
            tool="python-sha256",
            protocol_version=selected_config.version,
            benchmark=lambda: benchmark_cpu(
                block_bytes=selected_config.cpu_block_bytes,
                iterations=selected_config.cpu_iterations,
            ),
            clock=clock,
        ),
        _measurement(
            measurement_id=f"{resolved_sample_id}-memory",
            tool="python-memory-copy",
            protocol_version=selected_config.version,
            benchmark=lambda: benchmark_memory(
                block_bytes=selected_config.memory_block_bytes,
                iterations=selected_config.memory_iterations,
            ),
            clock=clock,
        ),
    ]

    if selected_config.include_storage:
        measurements.append(
            _measurement(
                measurement_id=f"{resolved_sample_id}-storage",
                tool="python-sequential-io",
                protocol_version=selected_config.version,
                benchmark=lambda: benchmark_storage(
                    block_bytes=selected_config.storage_block_bytes,
                    iterations=selected_config.storage_iterations,
                    fsync=selected_config.fsync_storage,
                    work_dir=work_dir,
                ),
                clock=clock,
            )
        )
    else:
        now = clock()
        measurements.append(
            Measurement(
                measurement_id=f"{resolved_sample_id}-storage",
                tool="python-sequential-io",
                tool_version=platform.python_version(),
                profile="general",
                protocol_version=selected_config.version,
                started_at=now,
                finished_at=now,
                status=MeasurementStatus.SKIPPED,
                error="storage benchmark disabled by configuration",
            )
        )

    warnings = list(discovered.warnings)
    if discovered.provider.provider_id is None and provider_id is None:
        warnings.append("provider_unknown")
    if discovered.hardware.memory_bytes is None:
        warnings.append("memory_capacity_unknown")

    failed = [
        measurement
        for measurement in measurements
        if measurement.status is MeasurementStatus.FAILED
    ]
    skipped = [
        measurement
        for measurement in measurements
        if measurement.status is MeasurementStatus.SKIPPED
    ]
    warnings.extend(f"measurement_failed:{item.tool}" for item in failed)
    warnings.extend(f"measurement_skipped:{item.tool}" for item in skipped)

    successful = [
        measurement
        for measurement in measurements
        if measurement.status is MeasurementStatus.SUCCESS
    ]
    errors: tuple[str, ...] = ()
    if not successful:
        quality_status = SampleQualityStatus.INVALID
        errors = ("no_successful_measurements",)
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
            profile="general",
            version=selected_config.version,
            fingerprint=selected_config.fingerprint,
        ),
        measurements=tuple(measurements),
        quality=SampleQuality(
            status=quality_status,
            warnings=tuple(dict.fromkeys(warnings)),
            errors=errors,
        ),
    )
