"""Tests for Agent Discovery data models and serialization."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from cloudeyes_agent.discovery import (
    DiscoveryConfidence,
    DiscoveryResult,
    HardwareInfo,
    NetworkInfo,
    ProviderInfo,
    SystemInfo,
    VirtualizationInfo,
    VirtualizationKind,
    dumps,
)


def make_result() -> DiscoveryResult:
    return DiscoveryResult(
        schema_version="1.0.0",
        discovered_at=datetime(2026, 8, 6, tzinfo=UTC),
        system=SystemInfo(
            os_name="Windows",
            os_version="10",
            kernel_version="10.0",
            architecture="AMD64",
            python_version="3.13.14",
            timezone="SE Asia Standard Time",
        ),
        hardware=HardwareInfo(
            architecture="AMD64",
            logical_cpu_count=8,
            physical_cpu_count=4,
            memory_bytes=17_179_869_184,
            cpu_model="Example CPU",
        ),
        virtualization=VirtualizationInfo(
            kind=VirtualizationKind.VIRTUAL_MACHINE,
            hypervisor="hyper-v",
            confidence=DiscoveryConfidence.HIGH,
            evidence=("system:microsoft corporation virtual machine",),
        ),
        provider=ProviderInfo(
            provider_id="azure",
            provider_name="Microsoft Azure",
            confidence=DiscoveryConfidence.MEDIUM,
            source="system",
            evidence=("system:azure",),
        ),
        network=NetworkInfo(
            interface_count=2,
            supports_ipv4=True,
            supports_ipv6=True,
            hostname_resolves=True,
        ),
    )


def test_hardware_rejects_zero_cpu_count() -> None:
    with pytest.raises(ValueError, match="logical_cpu_count"):
        HardwareInfo(
            architecture="x86_64",
            logical_cpu_count=0,
            physical_cpu_count=None,
            memory_bytes=None,
            cpu_model=None,
        )


def test_discovery_result_requires_timezone() -> None:
    result = make_result()
    with pytest.raises(ValueError, match="timezone"):
        DiscoveryResult(
            schema_version=result.schema_version,
            discovered_at=datetime(2026, 8, 6),
            system=result.system,
            hardware=result.hardware,
            virtualization=result.virtualization,
            provider=result.provider,
            network=result.network,
        )


def test_json_serialization_is_complete_and_privacy_safe() -> None:
    data = json.loads(dumps(make_result()))

    assert data["schema_version"] == "1.0.0"
    assert data["virtualization"]["kind"] == "virtual_machine"
    assert data["provider"]["provider_id"] == "azure"
    assert "hostname" not in data
    assert "username" not in data
    assert "ip_address" not in data
