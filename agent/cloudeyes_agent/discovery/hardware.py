"""Cross-platform, privacy-safe hardware discovery."""

from __future__ import annotations

import ctypes
import os
import platform
import re

from .model import HardwareInfo
from .utils import clean_optional, read_text, run_command


def _linux_memory_bytes() -> int | None:
    content = read_text("/proc/meminfo")
    if content is None:
        return None
    match = re.search(r"^MemTotal:\s+(\d+)\s+kB$", content, re.MULTILINE)
    return int(match.group(1)) * 1024 if match else None


def _windows_memory_bytes() -> int | None:
    class MemoryStatus(ctypes.Structure):
        _fields_ = [
            ("length", ctypes.c_ulong),
            ("memory_load", ctypes.c_ulong),
            ("total_physical", ctypes.c_ulonglong),
            ("available_physical", ctypes.c_ulonglong),
            ("total_page_file", ctypes.c_ulonglong),
            ("available_page_file", ctypes.c_ulonglong),
            ("total_virtual", ctypes.c_ulonglong),
            ("available_virtual", ctypes.c_ulonglong),
            ("available_extended_virtual", ctypes.c_ulonglong),
        ]

    try:
        status = MemoryStatus()
        status.length = ctypes.sizeof(MemoryStatus)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return None
        return int(status.total_physical)
    except (AttributeError, OSError, ValueError):
        return None


def _sysctl_integer(name: str) -> int | None:
    result = run_command(("sysctl", "-n", name))
    if result is None or result.returncode != 0:
        return None
    try:
        return int(result.stdout)
    except ValueError:
        return None


def _linux_cpu_model() -> str | None:
    content = read_text("/proc/cpuinfo")
    if content is None:
        return None
    for key in ("model name", "hardware", "processor"):
        match = re.search(rf"^{re.escape(key)}\s*:\s*(.+)$", content, re.MULTILINE | re.I)
        if match:
            return clean_optional(match.group(1))
    return None


def _linux_physical_cpu_count() -> int | None:
    content = read_text("/proc/cpuinfo")
    if content is None:
        return None

    blocks = re.split(r"\n\s*\n", content)
    cores: set[tuple[str, str]] = set()
    for block in blocks:
        physical = re.search(r"^physical id\s*:\s*(.+)$", block, re.MULTILINE)
        core = re.search(r"^core id\s*:\s*(.+)$", block, re.MULTILINE)
        if physical and core:
            cores.add((physical.group(1).strip(), core.group(1).strip()))
    if cores:
        return len(cores)

    match = re.search(r"^cpu cores\s*:\s*(\d+)$", content, re.MULTILINE)
    return int(match.group(1)) if match else None


def _windows_processor_data() -> tuple[int | None, str | None]:
    command = (
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        'Get-CimInstance Win32_Processor | ForEach-Object { "$($_.NumberOfCores)|$($_.Name)" }',
    )
    result = run_command(command, timeout=4.0)
    if result is None or result.returncode != 0 or not result.stdout:
        return None, None

    cores = 0
    names: list[str] = []
    for line in result.stdout.splitlines():
        raw_count, separator, raw_name = line.partition("|")
        if not separator:
            continue
        try:
            cores += int(raw_count.strip())
        except ValueError:
            pass
        name = clean_optional(raw_name)
        if name:
            names.append(name)

    return (cores or None), (names[0] if names else None)


def discover_hardware() -> HardwareInfo:
    """Collect CPU and memory capacity without unique machine identifiers."""

    system_name = platform.system().lower()
    logical_count = os.cpu_count() or 1
    physical_count: int | None = None
    memory_bytes: int | None = None
    cpu_model = clean_optional(platform.processor())

    if system_name == "linux":
        physical_count = _linux_physical_cpu_count()
        memory_bytes = _linux_memory_bytes()
        cpu_model = _linux_cpu_model() or cpu_model
    elif system_name == "windows":
        memory_bytes = _windows_memory_bytes()
        physical_count, windows_model = _windows_processor_data()
        cpu_model = windows_model or cpu_model
    elif system_name == "darwin":
        physical_count = _sysctl_integer("hw.physicalcpu")
        memory_bytes = _sysctl_integer("hw.memsize")
        result = run_command(("sysctl", "-n", "machdep.cpu.brand_string"))
        if result is not None and result.returncode == 0:
            cpu_model = clean_optional(result.stdout) or cpu_model

    return HardwareInfo(
        architecture=platform.machine() or "unknown",
        logical_cpu_count=logical_count,
        physical_cpu_count=physical_count,
        memory_bytes=memory_bytes,
        cpu_model=cpu_model,
    )
