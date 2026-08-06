"""Detect runtime tools that improve CloudEyes discovery and benchmarks."""

from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path

from .model import RuntimeDependencyReport

_REQUIRED_COMMANDS = ("lscpu", "free", "ip", "lspci")
_PACKAGE_MAP = {
    "apt-get": {
        "lscpu": "util-linux",
        "free": "procps",
        "ip": "iproute2",
        "lspci": "pciutils",
    },
    "dnf": {
        "lscpu": "util-linux",
        "free": "procps-ng",
        "ip": "iproute",
        "lspci": "pciutils",
    },
    "yum": {
        "lscpu": "util-linux",
        "free": "procps-ng",
        "ip": "iproute",
        "lspci": "pciutils",
    },
    "zypper": {
        "lscpu": "util-linux",
        "free": "procps",
        "ip": "iproute2",
        "lspci": "pciutils",
    },
    "apk": {
        "lscpu": "util-linux",
        "free": "procps",
        "ip": "iproute2",
        "lspci": "pciutils",
    },
    "pacman": {
        "lscpu": "util-linux",
        "free": "procps-ng",
        "ip": "iproute2",
        "lspci": "pciutils",
    },
}


def _find_package_manager() -> str | None:
    for command in _PACKAGE_MAP:
        if shutil.which(command):
            return command
    return None


def _read_os_id(path: Path = Path("/etc/os-release")) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def detect_runtime_dependencies() -> RuntimeDependencyReport:
    """Return missing optional tools and their native package names."""

    system = platform.system().lower()
    if system == "windows":
        return RuntimeDependencyReport(platform="windows", package_manager="winget")
    if system != "linux":
        return RuntimeDependencyReport(platform=system or os.name, package_manager=None)

    manager = _find_package_manager()
    missing = tuple(command for command in _REQUIRED_COMMANDS if shutil.which(command) is None)
    mapping = _PACKAGE_MAP.get(manager or "", {})
    packages = tuple(dict.fromkeys(mapping[command] for command in missing if command in mapping))

    os_id = _read_os_id().lower()
    platform_name = "linux"
    for name in (
        "sles",
        "opensuse",
        "ubuntu",
        "debian",
        "rhel",
        "centos",
        "rocky",
        "almalinux",
        "fedora",
        "alpine",
        "arch",
    ):
        if name in os_id:
            platform_name = name
            break

    return RuntimeDependencyReport(
        platform=platform_name,
        package_manager=manager,
        missing_commands=missing,
        packages=packages,
    )
