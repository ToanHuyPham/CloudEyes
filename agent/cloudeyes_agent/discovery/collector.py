"""Complete Agent Discovery pipeline."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import TypeVar

from .hardware import discover_hardware
from .model import (
    DiscoveryConfidence,
    DiscoveryResult,
    HardwareInfo,
    NetworkInfo,
    ProviderInfo,
    SystemInfo,
    VirtualizationInfo,
    VirtualizationKind,
)
from .network import discover_network
from .provider import discover_provider
from .system import discover_system
from .virtualization import collect_system_signals, discover_virtualization

_T = TypeVar("_T")


def _collect(
    name: str,
    function: Callable[[], _T],
    fallback: _T,
    warnings: list[str],
) -> _T:
    """Collect one section and preserve a usable result on platform errors."""

    try:
        return function()
    except Exception as error:  # pragma: no cover - defensive platform boundary
        warnings.append(f"{name}_discovery_failed:{type(error).__name__}")
        return fallback


def discover_all(
    *,
    discovered_at: datetime | None = None,
    env: Mapping[str, str] | None = None,
) -> DiscoveryResult:
    """Run the complete offline discovery pipeline."""

    environment = os.environ if env is None else env
    warnings: list[str] = []
    signals = _collect("signals", collect_system_signals, (), warnings)

    system = _collect(
        "system",
        discover_system,
        SystemInfo(
            os_name="unknown",
            os_version="unknown",
            kernel_version="unknown",
            architecture="unknown",
            python_version="unknown",
            timezone="unknown",
        ),
        warnings,
    )
    hardware = _collect(
        "hardware",
        discover_hardware,
        HardwareInfo(
            architecture="unknown",
            logical_cpu_count=1,
            physical_cpu_count=None,
            memory_bytes=None,
            cpu_model=None,
        ),
        warnings,
    )
    virtualization = _collect(
        "virtualization",
        lambda: discover_virtualization(env=environment, signals=signals),
        VirtualizationInfo(
            kind=VirtualizationKind.UNKNOWN,
            hypervisor=None,
            confidence=DiscoveryConfidence.LOW,
        ),
        warnings,
    )
    provider = _collect(
        "provider",
        lambda: discover_provider(env=environment, signals=signals),
        ProviderInfo(
            provider_id=None,
            provider_name=None,
            confidence=DiscoveryConfidence.LOW,
            source="unknown",
        ),
        warnings,
    )
    network = _collect(
        "network",
        discover_network,
        NetworkInfo(
            interface_count=0,
            supports_ipv4=False,
            supports_ipv6=False,
            hostname_resolves=False,
        ),
        warnings,
    )

    return DiscoveryResult(
        schema_version="1.0.0",
        discovered_at=discovered_at or datetime.now(UTC),
        system=system,
        hardware=hardware,
        virtualization=virtualization,
        provider=provider,
        network=network,
        warnings=tuple(warnings),
    )
