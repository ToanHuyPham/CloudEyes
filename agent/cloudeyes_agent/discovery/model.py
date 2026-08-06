"""Immutable data models produced by local environment discovery."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class DiscoveryConfidence(StrEnum):
    """Confidence assigned to an inferred discovery value."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class VirtualizationKind(StrEnum):
    """Broad execution environment type."""

    BARE_METAL = "bare_metal"
    VIRTUAL_MACHINE = "virtual_machine"
    CONTAINER = "container"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class SystemInfo:
    """Operating system and agent runtime information."""

    os_name: str
    os_version: str
    kernel_version: str
    architecture: str
    python_version: str
    timezone: str


@dataclass(frozen=True, slots=True)
class HardwareInfo:
    """Non-sensitive hardware capacity information."""

    architecture: str
    logical_cpu_count: int
    physical_cpu_count: int | None
    memory_bytes: int | None
    cpu_model: str | None

    def __post_init__(self) -> None:
        if self.logical_cpu_count < 1:
            raise ValueError("logical_cpu_count must be at least one")
        if self.physical_cpu_count is not None and self.physical_cpu_count < 1:
            raise ValueError("physical_cpu_count must be at least one")
        if self.memory_bytes is not None and self.memory_bytes < 1:
            raise ValueError("memory_bytes must be at least one")


@dataclass(frozen=True, slots=True)
class VirtualizationInfo:
    """Virtualization or container inference."""

    kind: VirtualizationKind
    hypervisor: str | None
    confidence: DiscoveryConfidence
    evidence: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class ProviderInfo:
    """Cloud provider inference without network metadata requests."""

    provider_id: str | None
    provider_name: str | None
    confidence: DiscoveryConfidence
    source: str
    evidence: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class NetworkInfo:
    """Privacy-safe local networking capabilities."""

    interface_count: int
    supports_ipv4: bool
    supports_ipv6: bool
    hostname_resolves: bool

    def __post_init__(self) -> None:
        if self.interface_count < 0:
            raise ValueError("interface_count must not be negative")


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    """Complete result of one local discovery run."""

    schema_version: str
    discovered_at: datetime
    system: SystemInfo
    hardware: HardwareInfo
    virtualization: VirtualizationInfo
    provider: ProviderInfo
    network: NetworkInfo
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.discovered_at.tzinfo is None:
            raise ValueError("discovered_at must contain timezone information")
