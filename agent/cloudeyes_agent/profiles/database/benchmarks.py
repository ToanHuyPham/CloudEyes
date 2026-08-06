"""Bounded SQLite workloads for CloudEyes Database Profile v1."""

from __future__ import annotations

import random
import shutil
import sqlite3
import statistics
import tempfile
import time
from collections import Counter
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from cloudeyes_core.models import Metric, MetricDirection

from ...execution import CancellationRequested, CancellationToken
from .config import DatabaseProfileConfig

Timer = Callable[[], float]
_MIB = 1024 * 1024
_EPSILON_SECONDS = 1e-9


class DatabaseSafetyError(RuntimeError):
    """Raised when the bounded database workload cannot run safely."""


@dataclass(frozen=True, slots=True)
class DatabaseBenchmarkResult:
    """Normalized metrics and privacy-safe raw database evidence."""

    metrics: tuple[Metric, ...]
    evidence: dict[str, Any]
    warnings: tuple[str, ...] = ()


def _checkpoint(token: CancellationToken | None) -> None:
    if token is not None:
        token.checkpoint()


def _elapsed(started: float, timer: Timer) -> float:
    return max(timer() - started, _EPSILON_SECONDS)


def _percentile(values: Sequence[float], fraction: float) -> float:
    if not values:
        raise ValueError("percentile values must not be empty")
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _connect(path: Path, config: DatabaseProfileConfig) -> sqlite3.Connection:
    connection = sqlite3.connect(
        path,
        timeout=config.busy_timeout_seconds,
        isolation_level=None,
        check_same_thread=True,
    )
    connection.execute(f"PRAGMA busy_timeout={int(config.busy_timeout_seconds * 1000)}")
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA synchronous=FULL")
    return connection


def _rollback_quietly(connection: sqlite3.Connection) -> None:
    try:
        connection.execute("ROLLBACK")
    except sqlite3.Error:
        pass


def _initialize_database(
    path: Path,
    config: DatabaseProfileConfig,
    *,
    cancellation_token: CancellationToken | None,
) -> str:
    payload = bytes(index % 251 for index in range(config.payload_bytes))
    connection = _connect(path, config)
    try:
        journal_mode = str(connection.execute("PRAGMA journal_mode=WAL").fetchone()[0]).lower()
        if journal_mode != "wal":
            raise DatabaseSafetyError("SQLite WAL journal mode could not be enabled")
        connection.execute(
            "CREATE TABLE records ("
            "id INTEGER PRIMARY KEY, "
            "payload BLOB NOT NULL, "
            "counter INTEGER NOT NULL DEFAULT 0"
            ")"
        )
        connection.execute("BEGIN IMMEDIATE")
        try:
            for start in range(1, config.record_count + 1, 500):
                _checkpoint(cancellation_token)
                stop = min(start + 500, config.record_count + 1)
                connection.executemany(
                    "INSERT INTO records(id, payload, counter) VALUES (?, ?, 0)",
                    ((record_id, payload) for record_id in range(start, stop)),
                )
            connection.execute("COMMIT")
        except BaseException:
            _rollback_quietly(connection)
            raise
    finally:
        connection.close()
    return journal_mode


def _warm_up(
    path: Path,
    config: DatabaseProfileConfig,
    *,
    cancellation_token: CancellationToken | None,
) -> None:
    if config.warmup_operations == 0:
        return
    connection = _connect(path, config)
    try:
        for index in range(config.warmup_operations):
            _checkpoint(cancellation_token)
            record_id = (index % config.record_count) + 1
            row = connection.execute(
                "SELECT length(payload), counter FROM records WHERE id = ?",
                (record_id,),
            ).fetchone()
            if row is None or row[0] != config.payload_bytes:
                raise RuntimeError("database warm-up verification failed")
    finally:
        connection.close()


def _connection_latencies(
    path: Path,
    config: DatabaseProfileConfig,
    *,
    timer: Timer,
    cancellation_token: CancellationToken | None,
) -> list[float]:
    latencies: list[float] = []
    for _ in range(config.connection_operations):
        _checkpoint(cancellation_token)
        started = timer()
        connection = _connect(path, config)
        try:
            row = connection.execute("SELECT 1").fetchone()
            if row != (1,):
                raise RuntimeError("database connection verification failed")
        finally:
            connection.close()
        latencies.append(_elapsed(started, timer) * 1000.0)
    return latencies


def _point_read_latencies(
    path: Path,
    config: DatabaseProfileConfig,
    *,
    repetition: int,
    timer: Timer,
    cancellation_token: CancellationToken | None,
) -> list[float]:
    generator = random.Random(config.random_seed + repetition * 101)
    record_ids = tuple(
        generator.randint(1, config.record_count) for _ in range(config.point_read_operations)
    )
    latencies: list[float] = []
    connection = _connect(path, config)
    try:
        for record_id in record_ids:
            _checkpoint(cancellation_token)
            started = timer()
            row = connection.execute(
                "SELECT length(payload), counter FROM records WHERE id = ?",
                (record_id,),
            ).fetchone()
            latencies.append(_elapsed(started, timer) * 1000.0)
            if row is None or row[0] != config.payload_bytes:
                raise RuntimeError("database point-read verification failed")
    finally:
        connection.close()
    return latencies


def _insert_transactions(
    path: Path,
    config: DatabaseProfileConfig,
    *,
    repetition: int,
    timer: Timer,
    cancellation_token: CancellationToken | None,
) -> tuple[float, list[float]]:
    payload = bytes((index + 17) % 251 for index in range(config.payload_bytes))
    first_id = config.record_count + repetition * config.insert_operations + 1
    connection = _connect(path, config)
    latencies: list[float] = []
    overall_started = timer()
    try:
        for offset in range(config.insert_operations):
            _checkpoint(cancellation_token)
            started = timer()
            try:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    "INSERT INTO records(id, payload, counter) VALUES (?, ?, 0)",
                    (first_id + offset, payload),
                )
                connection.execute("COMMIT")
            except BaseException:
                _rollback_quietly(connection)
                raise
            latencies.append(_elapsed(started, timer) * 1000.0)
    finally:
        elapsed = _elapsed(overall_started, timer)
        connection.close()
    return config.insert_operations / elapsed, latencies


def _update_transactions(
    path: Path,
    config: DatabaseProfileConfig,
    *,
    repetition: int,
    timer: Timer,
    cancellation_token: CancellationToken | None,
) -> tuple[float, list[float]]:
    generator = random.Random(config.random_seed + repetition * 103)
    record_ids = tuple(
        generator.randint(1, config.record_count) for _ in range(config.update_operations)
    )
    connection = _connect(path, config)
    latencies: list[float] = []
    overall_started = timer()
    try:
        for record_id in record_ids:
            _checkpoint(cancellation_token)
            started = timer()
            try:
                connection.execute("BEGIN IMMEDIATE")
                cursor = connection.execute(
                    "UPDATE records SET counter = counter + 1 WHERE id = ?",
                    (record_id,),
                )
                if cursor.rowcount != 1:
                    raise RuntimeError("database update verification failed")
                connection.execute("COMMIT")
            except BaseException:
                _rollback_quietly(connection)
                raise
            latencies.append(_elapsed(started, timer) * 1000.0)
    finally:
        elapsed = _elapsed(overall_started, timer)
        connection.close()
    return config.update_operations / elapsed, latencies


def _mixed_tasks(
    config: DatabaseProfileConfig,
    *,
    repetition: int,
) -> tuple[tuple[str, int], ...]:
    generator = random.Random(config.random_seed + repetition * 107)
    tasks: list[tuple[str, int]] = []
    for _ in range(config.mixed_operations):
        operation = "read" if generator.randrange(100) < config.mixed_read_percent else "update"
        tasks.append((operation, generator.randint(1, config.record_count)))
    return tuple(tasks)


def _mixed_worker(
    path: Path,
    config: DatabaseProfileConfig,
    tasks: Sequence[tuple[str, int]],
    cancellation_token: CancellationToken | None,
) -> dict[str, Any]:
    connection = _connect(path, config)
    completed = 0
    errors: Counter[str] = Counter()
    try:
        for operation, record_id in tasks:
            _checkpoint(cancellation_token)
            try:
                if operation == "read":
                    row = connection.execute(
                        "SELECT counter FROM records WHERE id = ?",
                        (record_id,),
                    ).fetchone()
                    if row is None:
                        raise RuntimeError("database mixed-read verification failed")
                else:
                    connection.execute("BEGIN IMMEDIATE")
                    cursor = connection.execute(
                        "UPDATE records SET counter = counter + 1 WHERE id = ?",
                        (record_id,),
                    )
                    if cursor.rowcount != 1:
                        raise RuntimeError("database mixed-update verification failed")
                    connection.execute("COMMIT")
                completed += 1
            except CancellationRequested:
                _rollback_quietly(connection)
                raise
            except sqlite3.Error as error:
                _rollback_quietly(connection)
                error_name = getattr(error, "sqlite_errorname", None) or type(error).__name__
                errors[str(error_name)] += 1
    finally:
        connection.close()
    return {
        "attempted": len(tasks),
        "completed": completed,
        "errors": dict(sorted(errors.items())),
    }


def _mixed_workload(
    path: Path,
    config: DatabaseProfileConfig,
    *,
    repetition: int,
    timer: Timer,
    cancellation_token: CancellationToken | None,
) -> dict[str, Any]:
    tasks = _mixed_tasks(config, repetition=repetition)
    partitions = tuple(tasks[index :: config.concurrency] for index in range(config.concurrency))
    started = timer()
    with ThreadPoolExecutor(
        max_workers=config.concurrency,
        thread_name_prefix="cloudeyes-database",
    ) as executor:
        futures = tuple(
            executor.submit(
                _mixed_worker,
                path,
                config,
                partition,
                cancellation_token,
            )
            for partition in partitions
        )
        results = tuple(future.result() for future in futures)
    elapsed = _elapsed(started, timer)

    attempted = sum(int(result["attempted"]) for result in results)
    completed = sum(int(result["completed"]) for result in results)
    error_counts: Counter[str] = Counter()
    for result in results:
        error_counts.update(result["errors"])
    errors = attempted - completed
    if completed == 0:
        raise OSError("all bounded mixed database operations failed")
    return {
        "attempted_operations": attempted,
        "completed_operations": completed,
        "elapsed_seconds": elapsed,
        "operations_per_second": completed / elapsed,
        "error_rate_percent": errors / attempted * 100.0,
        "error_type_counts": dict(sorted(error_counts.items())),
    }


def _run_repetition(
    path: Path,
    config: DatabaseProfileConfig,
    *,
    repetition: int,
    timer: Timer,
    cancellation_token: CancellationToken | None,
) -> dict[str, Any]:
    _checkpoint(cancellation_token)
    connection_latencies = _connection_latencies(
        path,
        config,
        timer=timer,
        cancellation_token=cancellation_token,
    )
    point_read_latencies = _point_read_latencies(
        path,
        config,
        repetition=repetition,
        timer=timer,
        cancellation_token=cancellation_token,
    )
    insert_tps, insert_latencies = _insert_transactions(
        path,
        config,
        repetition=repetition,
        timer=timer,
        cancellation_token=cancellation_token,
    )
    update_tps, update_latencies = _update_transactions(
        path,
        config,
        repetition=repetition,
        timer=timer,
        cancellation_token=cancellation_token,
    )
    mixed = _mixed_workload(
        path,
        config,
        repetition=repetition,
        timer=timer,
        cancellation_token=cancellation_token,
    )
    return {
        "repetition": repetition,
        "connection_latencies_ms": connection_latencies,
        "point_read_latencies_ms": point_read_latencies,
        "insert_transactions_per_second": insert_tps,
        "insert_transaction_latencies_ms": insert_latencies,
        "update_transactions_per_second": update_tps,
        "update_transaction_latencies_ms": update_latencies,
        "mixed": mixed,
    }


def benchmark_database_profile(
    *,
    config: DatabaseProfileConfig,
    work_dir: str | Path | None = None,
    timer: Timer = time.perf_counter,
    cancellation_token: CancellationToken | None = None,
) -> DatabaseBenchmarkResult:
    """Run a safe temporary SQLite workload and return normalized metrics."""

    _checkpoint(cancellation_token)
    parent = Path(work_dir) if work_dir is not None else Path.cwd()
    parent.mkdir(parents=True, exist_ok=True)

    estimated_database_bytes = max(
        8 * _MIB,
        config.record_count * (config.payload_bytes + 256) * 3,
    )
    required_free_bytes = estimated_database_bytes + 32 * _MIB
    free_bytes = shutil.disk_usage(parent).free
    if free_bytes < required_free_bytes:
        raise DatabaseSafetyError(
            f"insufficient free space: need {required_free_bytes} bytes, have {free_bytes} bytes"
        )

    warnings = ["database_profile_uses_local_sqlite"]
    if config.repetitions == 1:
        warnings.append("database_single_repetition")
    if config.concurrency == 1:
        warnings.append("database_concurrency_single_worker")

    runs: list[dict[str, Any]] = []
    file_sizes: dict[str, int] = {}
    journal_mode = config.journal_mode
    with tempfile.TemporaryDirectory(prefix="cloudeyes-database-", dir=parent) as temporary:
        database_path = Path(temporary) / "database.sqlite3"
        journal_mode = _initialize_database(
            database_path,
            config,
            cancellation_token=cancellation_token,
        )
        _warm_up(
            database_path,
            config,
            cancellation_token=cancellation_token,
        )
        for repetition in range(config.repetitions):
            runs.append(
                _run_repetition(
                    database_path,
                    config,
                    repetition=repetition,
                    timer=timer,
                    cancellation_token=cancellation_token,
                )
            )
        _checkpoint(cancellation_token)

        connection = _connect(database_path, config)
        try:
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        finally:
            connection.close()
        file_sizes = {
            "database_bytes": database_path.stat().st_size,
            "wal_bytes": database_path.with_name(f"{database_path.name}-wal").stat().st_size
            if database_path.with_name(f"{database_path.name}-wal").exists()
            else 0,
        }

    connection_latencies = [value for run in runs for value in run["connection_latencies_ms"]]
    point_read_latencies = [value for run in runs for value in run["point_read_latencies_ms"]]
    write_latencies = [
        value
        for run in runs
        for key in (
            "insert_transaction_latencies_ms",
            "update_transaction_latencies_ms",
        )
        for value in run[key]
    ]
    insert_rates = [run["insert_transactions_per_second"] for run in runs]
    update_rates = [run["update_transactions_per_second"] for run in runs]
    mixed_rates = [run["mixed"]["operations_per_second"] for run in runs]
    mixed_attempted = sum(run["mixed"]["attempted_operations"] for run in runs)
    mixed_completed = sum(run["mixed"]["completed_operations"] for run in runs)
    mixed_error_rate = (mixed_attempted - mixed_completed) / mixed_attempted * 100.0
    if mixed_error_rate > 0:
        warnings.append("database_mixed_operation_errors")

    aggregates = {
        "connection_p50_milliseconds": _percentile(connection_latencies, 0.50),
        "connection_p95_milliseconds": _percentile(connection_latencies, 0.95),
        "point_read_p50_milliseconds": _percentile(point_read_latencies, 0.50),
        "point_read_p95_milliseconds": _percentile(point_read_latencies, 0.95),
        "insert_transactions_per_second": statistics.median(insert_rates),
        "update_transactions_per_second": statistics.median(update_rates),
        "write_transaction_p95_milliseconds": _percentile(write_latencies, 0.95),
        "mixed_operations_per_second": statistics.median(mixed_rates),
        "mixed_error_rate_percent": mixed_error_rate,
    }
    metrics = (
        Metric(
            name="database.sqlite.connection.p50_milliseconds",
            value=aggregates["connection_p50_milliseconds"],
            unit="milliseconds",
            direction=MetricDirection.LOWER_IS_BETTER,
        ),
        Metric(
            name="database.sqlite.connection.p95_milliseconds",
            value=aggregates["connection_p95_milliseconds"],
            unit="milliseconds",
            direction=MetricDirection.LOWER_IS_BETTER,
        ),
        Metric(
            name="database.sqlite.point_read.p50_milliseconds",
            value=aggregates["point_read_p50_milliseconds"],
            unit="milliseconds",
            direction=MetricDirection.LOWER_IS_BETTER,
        ),
        Metric(
            name="database.sqlite.point_read.p95_milliseconds",
            value=aggregates["point_read_p95_milliseconds"],
            unit="milliseconds",
            direction=MetricDirection.LOWER_IS_BETTER,
        ),
        Metric(
            name="database.sqlite.insert.transactions_per_second",
            value=aggregates["insert_transactions_per_second"],
            unit="transactions_per_second",
            direction=MetricDirection.HIGHER_IS_BETTER,
        ),
        Metric(
            name="database.sqlite.update.transactions_per_second",
            value=aggregates["update_transactions_per_second"],
            unit="transactions_per_second",
            direction=MetricDirection.HIGHER_IS_BETTER,
        ),
        Metric(
            name="database.sqlite.write_transaction.p95_milliseconds",
            value=aggregates["write_transaction_p95_milliseconds"],
            unit="milliseconds",
            direction=MetricDirection.LOWER_IS_BETTER,
        ),
        Metric(
            name="database.sqlite.mixed.operations_per_second",
            value=aggregates["mixed_operations_per_second"],
            unit="operations_per_second",
            direction=MetricDirection.HIGHER_IS_BETTER,
        ),
        Metric(
            name="database.sqlite.mixed.error_rate.percent",
            value=aggregates["mixed_error_rate_percent"],
            unit="percent",
            direction=MetricDirection.LOWER_IS_BETTER,
        ),
    )
    evidence: dict[str, Any] = {
        "schema_version": "1.0.0",
        "profile": "database",
        "protocol_version": config.version,
        "engine": {
            "name": "sqlite",
            "version": sqlite3.sqlite_version,
            "journal_mode": journal_mode,
            "synchronous": config.synchronous,
        },
        "configuration": asdict(config),
        "safety": {
            "temporary_database": True,
            "free_bytes_before_run": free_bytes,
            "required_free_bytes": required_free_bytes,
            "estimated_database_bytes": estimated_database_bytes,
            "database_path_persisted": False,
        },
        "database_files_before_cleanup": file_sizes,
        "runs": runs,
        "aggregates": aggregates,
        "warnings": list(dict.fromkeys(warnings)),
        "limitations": [
            "Database Profile v1 measures a temporary local SQLite database, "
            "not a managed database service",
            "results combine Python, SQLite, CPU, memory, filesystem, "
            "and operating-system behavior",
            "WAL mode and synchronous FULL are fixed compatibility requirements",
            "mixed concurrency uses one SQLite connection per worker thread",
        ],
    }
    return DatabaseBenchmarkResult(
        metrics=metrics,
        evidence=evidence,
        warnings=tuple(dict.fromkeys(warnings)),
    )
