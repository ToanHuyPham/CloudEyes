"""End-to-end execution of the CloudEyes Storage Profile v1."""

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
)

from ...discovery import DiscoveryResult, VirtualizationKind, discover_all
from ...execution import CancellationRequested, CancellationToken
from ...reliability import ReliabilityPolicy, evaluate_sample_quality
from ...storage import write_raw_output
from .benchmarks import StorageBenchmarkResult, benchmark_storage_profile
from .config import StorageProfileConfig

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
    config: StorageProfileConfig,
    work_dir: str | Path | None,
    raw_output_dir: str | Path | None,
    clock: Clock,
    cancellation_token: CancellationToken | None = None,
) -> Measurement:
    started_at = clock()
    try:
        result: StorageBenchmarkResult = benchmark_storage_profile(
            config=config,
            work_dir=work_dir,
            cancellation_token=cancellation_token,
        )
        if cancellation_token is not None:
            cancellation_token.checkpoint()
        raw_output_path: str | None = None
        if raw_output_dir is not None:
            payload = dict(result.evidence)
            payload["sample_id"] = sample_id
            path = write_raw_output(
                payload,
                directory=raw_output_dir,
                stem=f"{sample_id}-storage",
            )
            raw_output_path = path.as_posix()
        if cancellation_token is not None:
            cancellation_token.checkpoint()
        return Measurement(
            measurement_id=f"{sample_id}-storage",
            tool="python-storage-profile",
            tool_version=platform.python_version(),
            profile="storage",
            protocol_version=config.version,
            started_at=started_at,
            finished_at=clock(),
            status=MeasurementStatus.SUCCESS,
            metrics=result.metrics,
            raw_output_path=raw_output_path,
        )
    except CancellationRequested:
        raise
    except Exception as error:  # pragma: no cover - behavior tested via monkeypatch
        return Measurement(
            measurement_id=f"{sample_id}-storage",
            tool="python-storage-profile",
            tool_version=platform.python_version(),
            profile="storage",
            protocol_version=config.version,
            started_at=started_at,
            finished_at=clock(),
            status=MeasurementStatus.FAILED,
            error=f"{type(error).__name__}: storage benchmark failed",
        )


def run_storage_profile(
    *,
    config: StorageProfileConfig | None = None,
    discovery: DiscoveryResult | None = None,
    sample_id: str | None = None,
    work_dir: str | Path | None = None,
    raw_output_dir: str | Path | None = None,
    provider_id: str | None = None,
    provider_name: str | None = None,
    country_code: str | None = None,
    product: str | None = None,
    plan: str | None = None,
    region: str | None = None,
    zone: str | None = None,
    clock: Clock = _utc_now,
    cancellation_token: CancellationToken | None = None,
) -> Sample:
    """Discover the host, run the storage workload, and build one Core sample."""

    if cancellation_token is not None:
        cancellation_token.checkpoint()

    selected_config = config or StorageProfileConfig()
    discovered = discovery or discover_all()
    resolved_sample_id = sample_id or f"storage-{uuid.uuid4().hex}"
    measurement = _measurement(
        sample_id=resolved_sample_id,
        config=selected_config,
        work_dir=work_dir,
        raw_output_dir=raw_output_dir,
        clock=clock,
        cancellation_token=cancellation_token,
    )

    warnings = list(discovered.warnings)
    if discovered.provider.provider_id is None and provider_id is None:
        warnings.append("provider_unknown")
    if discovered.hardware.memory_bytes is None:
        warnings.append("memory_capacity_unknown")
    if raw_output_dir is None:
        warnings.append("raw_output_not_persisted")

    quality = evaluate_sample_quality(
        (measurement,),
        warnings=tuple(warnings),
        invalid_error="storage_measurement_failed",
        policy=ReliabilityPolicy(max_measurement_seconds=900.0),
    )

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
            profile="storage",
            version=selected_config.version,
            fingerprint=selected_config.fingerprint,
        ),
        measurements=(measurement,),
        quality=quality,
    )
