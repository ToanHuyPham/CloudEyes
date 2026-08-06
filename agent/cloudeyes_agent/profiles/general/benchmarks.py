"""Portable built-in benchmarks used by the General Profile."""

from __future__ import annotations

import hashlib
import os
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

from cloudeyes_core.models import Metric, MetricDirection

_MIB = 1024 * 1024
_Timer = Callable[[], float]


def _elapsed(started_at: float, timer: _Timer) -> float:
    return max(timer() - started_at, 1e-9)


def _throughput_mib(total_bytes: int, elapsed_seconds: float) -> float:
    return total_bytes / _MIB / elapsed_seconds


def benchmark_cpu(
    *,
    block_bytes: int,
    iterations: int,
    timer: _Timer = time.perf_counter,
) -> tuple[Metric, ...]:
    """Measure single-process SHA-256 throughput with a fixed workload."""

    payload = b"CloudEyes-General-Profile" * (block_bytes // len(b"CloudEyes-General-Profile") + 1)
    payload = payload[:block_bytes]
    digest = b""

    started_at = timer()
    for _ in range(iterations):
        digest = hashlib.sha256(payload + digest).digest()
    elapsed_seconds = _elapsed(started_at, timer)

    if not digest:  # pragma: no cover - defensive guard
        raise RuntimeError("CPU benchmark did not produce a digest")

    return (
        Metric(
            name="compute.cpu.sha256_mib_per_second",
            value=_throughput_mib(block_bytes * iterations, elapsed_seconds),
            unit="mib_per_second",
            direction=MetricDirection.HIGHER_IS_BETTER,
        ),
    )


def benchmark_memory(
    *,
    block_bytes: int,
    iterations: int,
    timer: _Timer = time.perf_counter,
) -> tuple[Metric, ...]:
    """Measure in-process memory copy throughput."""

    source = bytearray(b"\xa5" * block_bytes)
    target = bytearray(block_bytes)

    started_at = timer()
    for _ in range(iterations):
        target[:] = source
    elapsed_seconds = _elapsed(started_at, timer)

    if target[0] != source[0]:  # pragma: no cover - defensive guard
        raise RuntimeError("memory benchmark copy verification failed")

    return (
        Metric(
            name="memory.copy.mib_per_second",
            value=_throughput_mib(block_bytes * iterations, elapsed_seconds),
            unit="mib_per_second",
            direction=MetricDirection.HIGHER_IS_BETTER,
        ),
    )


def benchmark_storage(
    *,
    block_bytes: int,
    iterations: int,
    fsync: bool,
    work_dir: str | Path | None = None,
    timer: _Timer = time.perf_counter,
) -> tuple[Metric, ...]:
    """Measure bounded sequential write and read throughput in a temporary file."""

    parent = Path(work_dir) if work_dir is not None else None
    if parent is not None:
        parent.mkdir(parents=True, exist_ok=True)

    block = b"\x5a" * block_bytes
    total_bytes = block_bytes * iterations

    with tempfile.TemporaryDirectory(dir=parent) as temporary_directory:
        path = Path(temporary_directory) / "cloudeyes-general-profile.bin"

        write_started = timer()
        with path.open("wb", buffering=0) as stream:
            for _ in range(iterations):
                stream.write(block)
            if fsync:
                os.fsync(stream.fileno())
        write_elapsed = _elapsed(write_started, timer)

        bytes_read = 0
        read_started = timer()
        with path.open("rb", buffering=0) as stream:
            while chunk := stream.read(block_bytes):
                bytes_read += len(chunk)
        read_elapsed = _elapsed(read_started, timer)

    if bytes_read != total_bytes:
        raise RuntimeError("storage benchmark read verification failed")

    return (
        Metric(
            name="storage.sequential_write.mib_per_second",
            value=_throughput_mib(total_bytes, write_elapsed),
            unit="mib_per_second",
            direction=MetricDirection.HIGHER_IS_BETTER,
        ),
        Metric(
            name="storage.sequential_read.mib_per_second",
            value=_throughput_mib(total_bytes, read_elapsed),
            unit="mib_per_second",
            direction=MetricDirection.HIGHER_IS_BETTER,
        ),
    )
