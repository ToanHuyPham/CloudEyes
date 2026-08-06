"""Portable CPU benchmarks for CloudEyes Compute Profile v1."""

from __future__ import annotations

import hashlib
import multiprocessing
import os
import platform
import random
import time
import zlib
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from statistics import median
from typing import Any

from cloudeyes_core.models import Metric, MetricDirection

from .config import ComputeProfileConfig

_MIB = 1024 * 1024
_Timer = Callable[[], float]
_MASK_64 = (1 << 64) - 1


@dataclass(frozen=True, slots=True)
class ComputeBenchmarkResult:
    """Normalized metrics, privacy-safe evidence, and explicit quality warnings."""

    metrics: tuple[Metric, ...]
    evidence: dict[str, Any]
    warnings: tuple[str, ...] = ()


def _elapsed(started_at: float, timer: _Timer) -> float:
    return max(timer() - started_at, 1e-12)


def _median(values: list[float]) -> float:
    if not values:
        raise ValueError("at least one timing sample is required")
    return float(median(values))


def _integer_kernel(iterations: int, seed: int) -> int:
    """Run a deterministic integer-mixing loop and return its checksum."""

    value = seed & _MASK_64
    for index in range(iterations):
        value ^= (value << 13) & _MASK_64
        value ^= value >> 7
        value ^= (value << 17) & _MASK_64
        value = (value + index + 0x9E3779B97F4A7C15) & _MASK_64
    return value


def _floating_point_kernel(iterations: int, seed: int) -> float:
    """Run deterministic scalar floating-point arithmetic."""

    value = 1.0 + (seed % 997) / 997.0
    accumulator = 0.0
    for index in range(iterations):
        value = value * 1.0000001192092896 + (index % 97) * 0.000001
        value = value / 1.0000000298023224
        if value > 10_000.0:
            value *= 0.0001
        accumulator += value
    return accumulator


def _sha256_kernel(block: bytes, iterations: int) -> str:
    digest = hashlib.sha256()
    for _ in range(iterations):
        digest.update(block)
    return digest.hexdigest()


def _compression_kernel(block: bytes, iterations: int, level: int) -> tuple[int, int]:
    total_output_bytes = 0
    checksum = 0
    for _ in range(iterations):
        compressed = zlib.compress(block, level)
        total_output_bytes += len(compressed)
        checksum ^= compressed[-1]
    return total_output_bytes, checksum


def _deterministic_block(size: int) -> bytes:
    generator = random.Random(0xC10DE5)
    return generator.randbytes(size)


def _available_cpu_count() -> int:
    get_affinity = getattr(os, "sched_getaffinity", None)
    if get_affinity is not None:
        try:
            return max(len(get_affinity(0)), 1)
        except OSError:
            pass
    return max(os.cpu_count() or 1, 1)


def _resolve_workers(config: ComputeProfileConfig) -> tuple[int, tuple[str, ...]]:
    available = _available_cpu_count()
    warnings: list[str] = []

    if config.workers == 0:
        workers = min(available, config.max_auto_workers)
        if available > config.max_auto_workers:
            warnings.append("compute_workers_auto_capped")
    else:
        workers = min(config.workers, available)
        if config.workers > available:
            warnings.append("compute_worker_count_capped_to_logical_cpus")

    if workers == 1:
        warnings.append("compute_single_worker_only")
    return workers, tuple(warnings)


def _integer_single_core(
    config: ComputeProfileConfig,
    *,
    timer: _Timer,
) -> tuple[list[float], list[int]]:
    rates: list[float] = []
    checksums: list[int] = []
    for repetition in range(config.repetitions):
        started_at = timer()
        checksum = _integer_kernel(config.integer_iterations, 101 + repetition)
        elapsed_seconds = _elapsed(started_at, timer)
        rates.append(config.integer_iterations / elapsed_seconds)
        checksums.append(checksum)
    return rates, checksums


def _integer_multi_core(
    config: ComputeProfileConfig,
    *,
    workers: int,
    timer: _Timer,
) -> tuple[list[float], list[int]]:
    rates: list[float] = []
    checksums: list[int] = []

    if workers == 1:
        for repetition in range(config.repetitions):
            started_at = timer()
            checksum = _integer_kernel(config.integer_iterations, 10_001 + repetition)
            elapsed_seconds = _elapsed(started_at, timer)
            rates.append(config.integer_iterations / elapsed_seconds)
            checksums.append(checksum)
        return rates, checksums

    with ProcessPoolExecutor(
        max_workers=workers,
        mp_context=multiprocessing.get_context("spawn"),
    ) as executor:
        warmups = [
            executor.submit(_integer_kernel, config.warmup_iterations, 50_000 + worker)
            for worker in range(workers)
        ]
        for future in warmups:
            future.result(timeout=config.worker_timeout_seconds)

        for repetition in range(config.repetitions):
            started_at = timer()
            futures = [
                executor.submit(
                    _integer_kernel,
                    config.integer_iterations,
                    100_000 + repetition * workers + worker,
                )
                for worker in range(workers)
            ]
            results = [future.result(timeout=config.worker_timeout_seconds) for future in futures]
            elapsed_seconds = _elapsed(started_at, timer)
            rates.append((config.integer_iterations * workers) / elapsed_seconds)
            checksums.append(sum(results) & _MASK_64)

    return rates, checksums


def benchmark_compute_profile(
    *,
    config: ComputeProfileConfig | None = None,
    timer: _Timer = time.perf_counter,
) -> ComputeBenchmarkResult:
    """Execute bounded CPU workloads and aggregate each metric with the median."""

    selected = config or ComputeProfileConfig()
    workers, warnings = _resolve_workers(selected)

    integer_warmup = max(1, min(selected.warmup_iterations, selected.integer_iterations))
    float_warmup = max(
        1,
        min(selected.warmup_iterations, selected.floating_point_iterations),
    )
    _integer_kernel(integer_warmup, 1)
    _floating_point_kernel(float_warmup, 1)

    sha_block = b"CloudEyes-Compute-v1" * (
        selected.sha256_block_bytes // len(b"CloudEyes-Compute-v1") + 1
    )
    sha_block = sha_block[: selected.sha256_block_bytes]
    compression_block = _deterministic_block(selected.compression_block_bytes)
    _sha256_kernel(sha_block[: min(len(sha_block), 64 * 1024)], 1)
    _compression_kernel(
        compression_block[: min(len(compression_block), 64 * 1024)],
        1,
        selected.compression_level,
    )

    integer_single_rates, integer_single_checksums = _integer_single_core(
        selected,
        timer=timer,
    )
    integer_multi_rates, integer_multi_checksums = _integer_multi_core(
        selected,
        workers=workers,
        timer=timer,
    )

    float_rates: list[float] = []
    float_checksums: list[float] = []
    for repetition in range(selected.repetitions):
        started_at = timer()
        checksum = _floating_point_kernel(
            selected.floating_point_iterations,
            201 + repetition,
        )
        elapsed_seconds = _elapsed(started_at, timer)
        float_rates.append(selected.floating_point_iterations / elapsed_seconds)
        float_checksums.append(checksum)

    sha_rates: list[float] = []
    sha_checksums: list[str] = []
    sha_total_bytes = selected.sha256_block_bytes * selected.sha256_iterations
    for _ in range(selected.repetitions):
        started_at = timer()
        checksum = _sha256_kernel(sha_block, selected.sha256_iterations)
        elapsed_seconds = _elapsed(started_at, timer)
        sha_rates.append((sha_total_bytes / _MIB) / elapsed_seconds)
        sha_checksums.append(checksum)

    compression_rates: list[float] = []
    compression_output_bytes: list[int] = []
    compression_checksums: list[int] = []
    compression_total_bytes = selected.compression_block_bytes * selected.compression_iterations
    for _ in range(selected.repetitions):
        started_at = timer()
        output_bytes, checksum = _compression_kernel(
            compression_block,
            selected.compression_iterations,
            selected.compression_level,
        )
        elapsed_seconds = _elapsed(started_at, timer)
        compression_rates.append((compression_total_bytes / _MIB) / elapsed_seconds)
        compression_output_bytes.append(output_bytes)
        compression_checksums.append(checksum)

    integer_single = _median(integer_single_rates)
    integer_multi = _median(integer_multi_rates)
    scaling_ratio = integer_multi / max(integer_single, 1e-12)
    worker_efficiency_percent = scaling_ratio / workers * 100.0

    metrics = (
        Metric(
            name="compute.integer.single_core.iterations_per_second",
            value=integer_single,
            unit="iterations_per_second",
            direction=MetricDirection.HIGHER_IS_BETTER,
        ),
        Metric(
            name="compute.integer.multi_core.iterations_per_second",
            value=integer_multi,
            unit="iterations_per_second",
            direction=MetricDirection.HIGHER_IS_BETTER,
        ),
        Metric(
            name="compute.floating_point.single_core.iterations_per_second",
            value=_median(float_rates),
            unit="iterations_per_second",
            direction=MetricDirection.HIGHER_IS_BETTER,
        ),
        Metric(
            name="compute.sha256.single_core.mib_per_second",
            value=_median(sha_rates),
            unit="mib_per_second",
            direction=MetricDirection.HIGHER_IS_BETTER,
        ),
        Metric(
            name="compute.compression.single_core.mib_per_second",
            value=_median(compression_rates),
            unit="mib_per_second",
            direction=MetricDirection.HIGHER_IS_BETTER,
        ),
        Metric(
            name="compute.concurrency.scaling_ratio",
            value=scaling_ratio,
            unit="ratio",
            direction=MetricDirection.HIGHER_IS_BETTER,
        ),
        Metric(
            name="compute.concurrency.worker_efficiency_percent",
            value=worker_efficiency_percent,
            unit="percent",
            direction=MetricDirection.HIGHER_IS_BETTER,
        ),
    )

    evidence: dict[str, Any] = {
        "schema_version": "1.0.0",
        "profile": "compute",
        "engine": "python-standard-library",
        "python": {
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
        },
        "configuration": asdict(selected),
        "execution": {
            "logical_cpu_count": _available_cpu_count(),
            "resolved_workers": workers,
            "aggregation": "median",
        },
        "samples": {
            "integer_single_iterations_per_second": integer_single_rates,
            "integer_multi_iterations_per_second": integer_multi_rates,
            "floating_point_iterations_per_second": float_rates,
            "sha256_mib_per_second": sha_rates,
            "compression_mib_per_second": compression_rates,
        },
        "verification": {
            "integer_single_checksums": integer_single_checksums,
            "integer_multi_checksums": integer_multi_checksums,
            "floating_point_checksums": float_checksums,
            "sha256_checksums": sha_checksums,
            "compression_output_bytes": compression_output_bytes,
            "compression_checksums": compression_checksums,
        },
        "limitations": [
            "Results include Python interpreter and standard-library implementation effects.",
            "Multi-core throughput uses worker processes and includes coordination overhead.",
            "CPU frequency, host contention, and thermal state can change between runs.",
        ],
    }
    return ComputeBenchmarkResult(metrics=metrics, evidence=evidence, warnings=warnings)
