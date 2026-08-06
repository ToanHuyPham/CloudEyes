"""Tests for CloudEyes Database Profile v1."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from cloudeyes_agent.execution import CancellationRequested
from cloudeyes_agent.profiles.database import (
    DatabaseBenchmarkResult,
    DatabaseProfileConfig,
    DatabaseSafetyError,
    benchmark_database_profile,
    run_database_profile,
)
from cloudeyes_agent.profiles.database import benchmarks as benchmark_module
from cloudeyes_agent.profiles.database import profile as profile_module
from cloudeyes_agent.storage import load_raw_output
from cloudeyes_core.models import Metric, MetricDirection, SampleQualityStatus
from cloudeyes_core.validation import validate_sample

from tests.unit.agent.test_discovery_models import make_result


def _result(*, warnings: tuple[str, ...] = ()) -> DatabaseBenchmarkResult:
    return DatabaseBenchmarkResult(
        metrics=(
            Metric(
                name="database.sqlite.mixed.operations_per_second",
                value=1_000.0,
                unit="operations_per_second",
                direction=MetricDirection.HIGHER_IS_BETTER,
            ),
        ),
        evidence={"schema_version": "1.0.0", "profile": "database"},
        warnings=warnings,
    )


def test_database_config_is_bounded_and_fingerprint_is_stable() -> None:
    config = DatabaseProfileConfig()

    assert config.fingerprint == DatabaseProfileConfig().fingerprint
    assert len(config.fingerprint) == 64
    assert config.record_count * config.payload_bytes <= 128 * 1024 * 1024
    assert config.journal_mode == "wal"
    assert config.synchronous == "full"


def test_database_config_rejects_unsupported_or_unbounded_workloads() -> None:
    with pytest.raises(ValueError, match="sqlite"):
        DatabaseProfileConfig(engine="postgresql")
    with pytest.raises(ValueError, match="journal_mode"):
        DatabaseProfileConfig(journal_mode="delete")
    with pytest.raises(ValueError, match="total bounded database operations"):
        DatabaseProfileConfig(
            point_read_operations=100_000,
            mixed_operations=100_000,
            repetitions=3,
        )


def test_database_config_fingerprint_tracks_workload() -> None:
    base = DatabaseProfileConfig.quick()

    assert base.fingerprint != replace(base, record_count=300).fingerprint
    assert base.fingerprint != replace(base, concurrency=1).fingerprint


def test_quick_database_benchmark_returns_metrics_and_privacy_safe_evidence(
    tmp_path,
) -> None:
    result = benchmark_database_profile(
        config=DatabaseProfileConfig.quick(),
        work_dir=tmp_path,
    )

    metric_names = {metric.name for metric in result.metrics}
    assert metric_names == {
        "database.sqlite.connection.p50_milliseconds",
        "database.sqlite.connection.p95_milliseconds",
        "database.sqlite.point_read.p50_milliseconds",
        "database.sqlite.point_read.p95_milliseconds",
        "database.sqlite.insert.transactions_per_second",
        "database.sqlite.update.transactions_per_second",
        "database.sqlite.write_transaction.p95_milliseconds",
        "database.sqlite.mixed.operations_per_second",
        "database.sqlite.mixed.error_rate.percent",
    }
    assert all(metric.value >= 0 for metric in result.metrics)
    assert result.evidence["engine"]["journal_mode"] == "wal"
    assert result.evidence["safety"]["temporary_database"] is True
    assert result.evidence["safety"]["database_path_persisted"] is False
    evidence_text = json.dumps(result.evidence)
    assert str(tmp_path) not in evidence_text
    assert not tuple(tmp_path.glob("cloudeyes-database-*"))


def test_database_benchmark_rejects_insufficient_free_space(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        benchmark_module.shutil,
        "disk_usage",
        lambda _: SimpleNamespace(free=1),
    )

    with pytest.raises(DatabaseSafetyError, match="insufficient free space"):
        benchmark_database_profile(
            config=DatabaseProfileConfig.quick(),
            work_dir=tmp_path,
        )


def test_database_profile_builds_valid_sample_and_raw_evidence(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(profile_module, "benchmark_database_profile", lambda **_: _result())
    fixed_time = datetime(2026, 8, 6, 18, 0, tzinfo=UTC)

    sample = run_database_profile(
        config=DatabaseProfileConfig.quick(),
        discovery=make_result(),
        sample_id="database-test",
        work_dir=tmp_path,
        raw_output_dir=tmp_path / "raw",
        country_code="VN",
        clock=lambda: fixed_time,
    )

    assert sample.protocol.profile == "database"
    assert sample.quality.status is SampleQualityStatus.VALID
    assert validate_sample(sample).valid is True
    raw_path = sample.measurements[0].raw_output_path
    assert raw_path is not None
    assert load_raw_output(raw_path)["profile"] == "database"


def test_database_profile_propagates_explicit_limitations(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        profile_module,
        "benchmark_database_profile",
        lambda **_: _result(warnings=("database_profile_uses_local_sqlite",)),
    )

    sample = run_database_profile(
        config=DatabaseProfileConfig.quick(),
        discovery=make_result(),
        sample_id="database-warning",
        work_dir=tmp_path,
        raw_output_dir=tmp_path / "raw",
    )

    assert "database_profile_uses_local_sqlite" in sample.quality.warnings
    assert sample.quality.status is SampleQualityStatus.VALID_WITH_WARNINGS


def test_database_benchmark_failure_creates_invalid_sample(monkeypatch) -> None:
    def fail(**_):
        raise RuntimeError("database failed")

    monkeypatch.setattr(profile_module, "benchmark_database_profile", fail)
    sample = run_database_profile(
        config=DatabaseProfileConfig.quick(),
        discovery=make_result(),
        sample_id="database-failed",
    )

    assert sample.measurements[0].status.value == "failed"
    assert sample.quality.status is SampleQualityStatus.INVALID
    assert sample.quality.errors == ("database_measurement_failed",)


def test_database_cancellation_removes_temporary_files(tmp_path, monkeypatch) -> None:
    def cancel(*_, **__):
        raise CancellationRequested("stop")

    monkeypatch.setattr(benchmark_module, "_run_repetition", cancel)

    with pytest.raises(CancellationRequested):
        benchmark_database_profile(
            config=DatabaseProfileConfig.quick(),
            work_dir=tmp_path,
        )

    assert not tuple(tmp_path.glob("cloudeyes-database-*"))
