"""Virtual machine and container discovery."""

from __future__ import annotations

import os
import platform
from collections.abc import Mapping
from pathlib import Path

from .model import DiscoveryConfidence, VirtualizationInfo, VirtualizationKind
from .utils import lower_signals, read_text, run_command

_DMI_PATHS = (
    "/sys/class/dmi/id/sys_vendor",
    "/sys/class/dmi/id/product_name",
    "/sys/class/dmi/id/product_version",
    "/sys/class/dmi/id/board_vendor",
)

_HYPERVISORS = (
    ("amazon ec2", "amazon-nitro"),
    ("google compute engine", "google-kvm"),
    ("microsoft corporation virtual machine", "hyper-v"),
    ("vmware", "vmware"),
    ("virtualbox", "virtualbox"),
    ("kvm", "kvm"),
    ("qemu", "qemu"),
    ("xen", "xen"),
    ("openstack", "openstack"),
    ("parallels", "parallels"),
    ("bochs", "bochs"),
)


def collect_system_signals() -> tuple[str, ...]:
    """Collect non-sensitive manufacturer and virtualization strings."""

    values: list[str | None] = [platform.platform(), platform.processor()]
    if platform.system().lower() == "linux":
        values.extend(read_text(path) for path in _DMI_PATHS)
    elif platform.system().lower() == "windows":
        command = (
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "Get-CimInstance Win32_ComputerSystem | "
            'ForEach-Object { "$($_.Manufacturer) $($_.Model)" }',
        )
        result = run_command(command, timeout=4.0)
        if result is not None and result.returncode == 0:
            values.append(result.stdout)
    return lower_signals(values)


def _container_evidence(env: Mapping[str, str]) -> tuple[str, ...]:
    evidence: list[str] = []
    if Path("/.dockerenv").exists():
        evidence.append("file:/.dockerenv")
    if Path("/run/.containerenv").exists():
        evidence.append("file:/run/.containerenv")
    if "KUBERNETES_SERVICE_HOST" in env:
        evidence.append("environment:KUBERNETES_SERVICE_HOST")

    cgroup = read_text("/proc/1/cgroup") or ""
    for marker in ("docker", "containerd", "kubepods", "podman", "lxc"):
        if marker in cgroup.lower():
            evidence.append(f"cgroup:{marker}")
            break
    return tuple(evidence)


def discover_virtualization(
    *,
    env: Mapping[str, str] | None = None,
    signals: tuple[str, ...] | None = None,
) -> VirtualizationInfo:
    """Infer virtualization without contacting a provider metadata endpoint."""

    environment = os.environ if env is None else env
    container_evidence = _container_evidence(environment)
    if container_evidence:
        hypervisor = "kubernetes" if "KUBERNETES_SERVICE_HOST" in environment else "container"
        return VirtualizationInfo(
            kind=VirtualizationKind.CONTAINER,
            hypervisor=hypervisor,
            confidence=DiscoveryConfidence.HIGH,
            evidence=container_evidence,
        )

    system_signals = collect_system_signals() if signals is None else lower_signals(signals)
    combined = " | ".join(system_signals)
    for marker, hypervisor in _HYPERVISORS:
        if marker in combined:
            return VirtualizationInfo(
                kind=VirtualizationKind.VIRTUAL_MACHINE,
                hypervisor=hypervisor,
                confidence=DiscoveryConfidence.HIGH,
                evidence=(f"system:{marker}",),
            )

    if platform.system().lower() == "linux":
        result = run_command(("systemd-detect-virt",))
        if result is not None:
            detected = result.stdout.strip().lower()
            if result.returncode == 0 and detected and detected != "none":
                return VirtualizationInfo(
                    kind=VirtualizationKind.VIRTUAL_MACHINE,
                    hypervisor=detected,
                    confidence=DiscoveryConfidence.MEDIUM,
                    evidence=("command:systemd-detect-virt",),
                )
            if result.returncode != 0 or detected == "none":
                return VirtualizationInfo(
                    kind=VirtualizationKind.BARE_METAL,
                    hypervisor=None,
                    confidence=DiscoveryConfidence.MEDIUM,
                    evidence=("command:systemd-detect-virt:none",),
                )

    return VirtualizationInfo(
        kind=VirtualizationKind.UNKNOWN,
        hypervisor=None,
        confidence=DiscoveryConfidence.LOW,
    )
