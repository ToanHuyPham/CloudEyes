"""Tests for virtualization inference."""

from __future__ import annotations

from cloudeyes_agent.discovery import VirtualizationKind, discover_virtualization
from cloudeyes_agent.discovery import virtualization as module


def test_kubernetes_environment_is_a_container(monkeypatch) -> None:
    monkeypatch.setattr(module, "_container_evidence", lambda env: ("environment:test",))

    result = discover_virtualization(
        env={"KUBERNETES_SERVICE_HOST": "internal"},
        signals=(),
    )

    assert result.kind is VirtualizationKind.CONTAINER
    assert result.hypervisor == "kubernetes"


def test_known_dmi_signal_is_a_virtual_machine(monkeypatch) -> None:
    monkeypatch.setattr(module, "_container_evidence", lambda env: ())

    result = discover_virtualization(
        env={},
        signals=("Microsoft Corporation Virtual Machine",),
    )

    assert result.kind is VirtualizationKind.VIRTUAL_MACHINE
    assert result.hypervisor == "hyper-v"


def test_unknown_signal_remains_unknown(monkeypatch) -> None:
    monkeypatch.setattr(module, "_container_evidence", lambda env: ())
    monkeypatch.setattr(module.platform, "system", lambda: "Windows")

    result = discover_virtualization(env={}, signals=("Custom Workstation",))

    assert result.kind is VirtualizationKind.UNKNOWN
