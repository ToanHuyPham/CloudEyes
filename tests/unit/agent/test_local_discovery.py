"""Portable smoke tests for local discovery collectors."""

from __future__ import annotations

from cloudeyes_agent.discovery import (
    discover_all,
    discover_hardware,
    discover_network,
    discover_system,
)


def test_system_discovery_returns_required_values() -> None:
    result = discover_system()

    assert result.os_name
    assert result.kernel_version
    assert result.architecture
    assert result.python_version
    assert result.timezone


def test_hardware_discovery_has_at_least_one_logical_cpu() -> None:
    result = discover_hardware()

    assert result.logical_cpu_count >= 1
    assert result.architecture


def test_network_discovery_does_not_expose_addresses() -> None:
    result = discover_network()

    assert result.interface_count >= 0
    assert not hasattr(result, "addresses")
    assert not hasattr(result, "hostname")


def test_complete_discovery_runs_offline() -> None:
    result = discover_all(env={})

    assert result.schema_version == "1.0.0"
    assert result.discovered_at.tzinfo is not None
    assert result.hardware.logical_cpu_count >= 1


def test_complete_discovery_keeps_working_when_one_collector_fails(monkeypatch) -> None:
    from cloudeyes_agent.discovery import collector

    def fail_hardware():
        raise OSError("not available")

    monkeypatch.setattr(collector, "discover_hardware", fail_hardware)
    result = collector.discover_all(env={})

    assert result.hardware.logical_cpu_count == 1
    assert "hardware_discovery_failed:OSError" in result.warnings
