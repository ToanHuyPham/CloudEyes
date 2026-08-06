"""Portable bounded benchmarks for the CloudEyes Storage Profile v1."""

from __future__ import annotations

import os
import random
import shutil
import statistics
import tempfile
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from cloudeyes_core.models import Metric, MetricDirection

from ...execution import CancellationToken
from .config import StorageProfileConfig

_MIB = 1024 * 1024
_Timer = Callable[[], float]


class StorageSafetyError(RuntimeError):
    """Raised when the requested storage workload is unsafe for the target."""


@dataclass(frozen=True, slots=True)
class StorageBenchmarkResult:
    """Normalized metrics and raw evidence from one storage benchmark run."""

    metrics: tuple[Metric, ...]
    evidence: dict[str, Any]


def _elapsed(started_at: float, timer: _Timer) -> float:
    return max(timer() - started_at, 1e-9)


def _throughput_mib(total_bytes: int, elapsed_seconds: float) -> float:
    return total_bytes / _MIB / elapsed_seconds


def _checkpoint(token: CancellationToken | None) -> None:
    if token is not None:
        token.checkpoint()


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        raise ValueError("percentile requires at least one value")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _write_file(
    path: Path,
    *,
    file_size: int,
    block_size: int,
    fsync: bool,
    cancellation_token: CancellationToken | None = None,
) -> None:
    block = b"\xa5" * block_size
    remaining = file_size
    with path.open("wb", buffering=0) as stream:
        while remaining:
            _checkpoint(cancellation_token)
            chunk = block if remaining >= block_size else block[:remaining]
            stream.write(chunk)
            remaining -= len(chunk)
        if fsync:
            os.fsync(stream.fileno())


def _warm_up(
    path: Path,
    config: StorageProfileConfig,
    *,
    cancellation_token: CancellationToken | None = None,
) -> None:
    if config.warmup_operations == 0:
        return
    block = b"\x5a" * config.random_block_bytes
    slots = max(1, config.file_size_bytes // config.random_block_bytes)
    with path.open("r+b", buffering=0) as stream:
        for index in range(config.warmup_operations):
            _checkpoint(cancellation_token)
            stream.seek((index % slots) * config.random_block_bytes)
            stream.write(block)
        stream.flush()
        if config.fsync_writes:
            os.fsync(stream.fileno())


def _random_offsets(config: StorageProfileConfig, *, repetition: int) -> tuple[int, ...]:
    slots = max(1, config.file_size_bytes // config.random_block_bytes)
    generator = random.Random(config.random_seed + repetition)
    return tuple(
        generator.randrange(slots) * config.random_block_bytes
        for _ in range(config.random_operations)
    )


def _run_repetition(
    path: Path,
    config: StorageProfileConfig,
    *,
    repetition: int,
    timer: _Timer,
    cancellation_token: CancellationToken | None = None,
) -> dict[str, Any]:
    sequential_block = b"\xc3" * config.sequential_block_bytes
    random_block = b"\x3c" * config.random_block_bytes

    _checkpoint(cancellation_token)
    remaining = config.file_size_bytes
    write_started = timer()
    with path.open("wb", buffering=0) as stream:
        while remaining:
            _checkpoint(cancellation_token)
            chunk = (
                sequential_block
                if remaining >= config.sequential_block_bytes
                else sequential_block[:remaining]
            )
            stream.write(chunk)
            remaining -= len(chunk)
        stream.flush()
        if config.fsync_writes:
            os.fsync(stream.fileno())
    sequential_write_seconds = _elapsed(write_started, timer)

    bytes_read = 0
    read_started = timer()
    with path.open("rb", buffering=0) as stream:
        while chunk := stream.read(config.sequential_block_bytes):
            _checkpoint(cancellation_token)
            bytes_read += len(chunk)
    sequential_read_seconds = _elapsed(read_started, timer)
    if bytes_read != config.file_size_bytes:
        raise RuntimeError("sequential read verification failed")

    offsets = _random_offsets(config, repetition=repetition)
    random_read_started = timer()
    with path.open("rb", buffering=0) as stream:
        for offset in offsets:
            _checkpoint(cancellation_token)
            stream.seek(offset)
            chunk = stream.read(config.random_block_bytes)
            if len(chunk) != config.random_block_bytes:
                raise RuntimeError("random read verification failed")
    random_read_seconds = _elapsed(random_read_started, timer)

    random_write_started = timer()
    with path.open("r+b", buffering=0) as stream:
        for offset in offsets:
            _checkpoint(cancellation_token)
            stream.seek(offset)
            stream.write(random_block)
        stream.flush()
        if config.fsync_writes:
            os.fsync(stream.fileno())
    random_write_seconds = _elapsed(random_write_started, timer)

    slots = max(1, config.file_size_bytes // config.random_block_bytes)
    fsync_latencies_ms: list[float] = []
    with path.open("r+b", buffering=0) as stream:
        for index in range(config.fsync_operations):
            _checkpoint(cancellation_token)
            stream.seek((index % slots) * config.random_block_bytes)
            stream.write(random_block)
            stream.flush()
            fsync_started = timer()
            os.fsync(stream.fileno())
            fsync_latencies_ms.append(_elapsed(fsync_started, timer) * 1000.0)

    return {
        "repetition": repetition,
        "sequential_write_mib_per_second": _throughput_mib(
            config.file_size_bytes,
            sequential_write_seconds,
        ),
        "sequential_read_mib_per_second": _throughput_mib(
            config.file_size_bytes,
            sequential_read_seconds,
        ),
        "random_read_iops": config.random_operations / random_read_seconds,
        "random_write_iops": config.random_operations / random_write_seconds,
        "fsync_latencies_ms": fsync_latencies_ms,
    }


def benchmark_storage_profile(
    *,
    config: StorageProfileConfig,
    work_dir: str | Path | None = None,
    timer: _Timer = time.perf_counter,
    cancellation_token: CancellationToken | None = None,
) -> StorageBenchmarkResult:
    """Run a safe temporary-file storage workload and return normalized metrics."""

    _checkpoint(cancellation_token)
    parent = Path(work_dir) if work_dir is not None else Path.cwd()
    parent.mkdir(parents=True, exist_ok=True)

    required_free = max(config.file_size_bytes * 2, 64 * _MIB)
    available = shutil.disk_usage(parent).free
    if available < required_free:
        raise StorageSafetyError(
            f"insufficient free space: need {required_free} bytes, have {available} bytes"
        )

    runs: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="cloudeyes-storage-", dir=parent) as temporary:
        temporary_path = Path(temporary)
        warmup_path = temporary_path / "warmup.bin"
        _write_file(
            warmup_path,
            file_size=config.file_size_bytes,
            block_size=config.sequential_block_bytes,
            fsync=config.fsync_writes,
            cancellation_token=cancellation_token,
        )
        _warm_up(
            warmup_path,
            config,
            cancellation_token=cancellation_token,
        )
        warmup_path.unlink()

        for repetition in range(config.repetitions):
            _checkpoint(cancellation_token)
            path = temporary_path / f"storage-{repetition}.bin"
            runs.append(
                _run_repetition(
                    path,
                    config,
                    repetition=repetition,
                    timer=timer,
                    cancellation_token=cancellation_token,
                )
            )
            path.unlink()
        _checkpoint(cancellation_token)

    sequential_writes = [run["sequential_write_mib_per_second"] for run in runs]
    sequential_reads = [run["sequential_read_mib_per_second"] for run in runs]
    random_reads = [run["random_read_iops"] for run in runs]
    random_writes = [run["random_write_iops"] for run in runs]
    fsync_latencies = [value for run in runs for value in run["fsync_latencies_ms"]]

    aggregates = {
        "sequential_write_mib_per_second": statistics.median(sequential_writes),
        "sequential_read_mib_per_second": statistics.median(sequential_reads),
        "random_read_iops": statistics.median(random_reads),
        "random_write_iops": statistics.median(random_writes),
        "fsync_p50_milliseconds": _percentile(fsync_latencies, 0.50),
        "fsync_p95_milliseconds": _percentile(fsync_latencies, 0.95),
    }
    metrics = (
        Metric(
            name="storage.sequential_write.fsync_mib_per_second",
            value=aggregates["sequential_write_mib_per_second"],
            unit="mib_per_second",
            direction=MetricDirection.HIGHER_IS_BETTER,
        ),
        Metric(
            name="storage.sequential_read.cached_mib_per_second",
            value=aggregates["sequential_read_mib_per_second"],
            unit="mib_per_second",
            direction=MetricDirection.HIGHER_IS_BETTER,
        ),
        Metric(
            name="storage.random_read.cached_iops",
            value=aggregates["random_read_iops"],
            unit="operations_per_second",
            direction=MetricDirection.HIGHER_IS_BETTER,
        ),
        Metric(
            name="storage.random_write.fsync_batch_iops",
            value=aggregates["random_write_iops"],
            unit="operations_per_second",
            direction=MetricDirection.HIGHER_IS_BETTER,
        ),
        Metric(
            name="storage.fsync.p50_milliseconds",
            value=aggregates["fsync_p50_milliseconds"],
            unit="milliseconds",
            direction=MetricDirection.LOWER_IS_BETTER,
        ),
        Metric(
            name="storage.fsync.p95_milliseconds",
            value=aggregates["fsync_p95_milliseconds"],
            unit="milliseconds",
            direction=MetricDirection.LOWER_IS_BETTER,
        ),
    )
    evidence: dict[str, Any] = {
        "schema_version": "1.0.0",
        "profile": "storage",
        "protocol_version": config.version,
        "configuration": asdict(config),
        "filesystem": {
            "work_directory": str(parent),
            "free_bytes_before_run": available,
        },
        "runs": runs,
        "aggregates": aggregates,
        "limitations": [
            "sequential read and random read may use operating-system page cache",
            "results describe the tested filesystem path, not every provider storage product",
            "random I/O is single-process and queue-depth one",
        ],
    }
    return StorageBenchmarkResult(metrics=metrics, evidence=evidence)
