"""Tests for the complete Storage Profile v1."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from cloudeyes_agent.profiles.storage import (
    StorageBenchmarkResult,
    StorageProfileConfig,
    StorageSafetyError,
    benchmark_storage_profile,
    run_storage_profile,
)
from cloudeyes_agent.profiles.storage import profile as profile_module
from cloudeyes_core.models import Metric, MetricDirection, SampleQualityStatus
from cloudeyes_core.validation import validate_sample

from tests.unit.agent.test_discovery_models import make_result


def _result() -> StorageBenchmarkResult:
    return StorageBenchmarkResult(
        metrics=(
            Metric(
                name="storage.sequential_write.fsync_mib_per_second",
                value=100.0,
                unit="mib_per_second",
                direction=MetricDirection.HIGHER_IS_BETTER,
            ),
        ),
        evidence={"schema_version": "1.0.0", "runs": []},
    )


def test_default_config_is_bounded_and_fingerprint_is_stable() -> None:
    first = StorageProfileConfig()
    second = StorageProfileConfig()

    assert first.fingerprint == second.fingerprint
    assert len(first.fingerprint) == 64
    assert first.file_size_bytes <= 1024 * 1024 * 1024


def test_config_rejects_oversized_file() -> None:
    with pytest.raises(ValueError, match="file_size_bytes"):
        StorageProfileConfig(file_size_bytes=2 * 1024 * 1024 * 1024)


def test_config_rejects_sequential_block_larger_than_file() -> None:
    with pytest.raises(ValueError, match="sequential_block_bytes"):
        StorageProfileConfig(
            file_size_bytes=1024 * 1024,
            sequential_block_bytes=2 * 1024 * 1024,
        )


def test_quick_benchmark_returns_all_metrics_and_cleans_up(tmp_path) -> None:
    result = benchmark_storage_profile(
        config=StorageProfileConfig.quick(),
        work_dir=tmp_path,
    )

    assert {metric.name for metric in result.metrics} == {
        "storage.fsync.p50_milliseconds",
        "storage.fsync.p95_milliseconds",
        "storage.random_read.cached_iops",
        "storage.random_write.fsync_batch_iops",
        "storage.sequential_read.cached_mib_per_second",
        "storage.sequential_write.fsync_mib_per_second",
    }
    assert all(metric.value > 0 for metric in result.metrics)
    assert result.evidence["profile"] == "storage"
    assert not any(tmp_path.iterdir())


def test_benchmark_rejects_insufficient_free_space(tmp_path, monkeypatch) -> None:
    usage = type("Usage", (), {"free": 1})()
    monkeypatch.setattr(
        "cloudeyes_agent.profiles.storage.benchmarks.shutil.disk_usage",
        lambda _: usage,
    )

    with pytest.raises(StorageSafetyError, match="insufficient free space"):
        benchmark_storage_profile(
            config=StorageProfileConfig.quick(),
            work_dir=tmp_path,
        )


def test_profile_builds_valid_sample_and_raw_evidence(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(profile_module, "benchmark_storage_profile", lambda **_: _result())
    fixed_time = datetime(2026, 8, 6, 13, 0, tzinfo=UTC)

    sample = run_storage_profile(
        config=StorageProfileConfig.quick(),
        discovery=make_result(),
        sample_id="storage-test",
        work_dir=tmp_path,
        raw_output_dir=tmp_path / "raw",
        country_code="VN",
        product="Persistent Disk",
        plan="balanced",
        region="asia-southeast1",
        zone="asia-southeast1-a",
        clock=lambda: fixed_time,
    )

    assert sample.protocol.profile == "storage"
    assert sample.measurements[0].raw_output_path is not None
    assert sample.quality.status is SampleQualityStatus.VALID
    assert validate_sample(sample).valid is True
    assert (tmp_path / "raw" / "storage-test-storage.json").exists()


def test_missing_raw_output_is_explicit_warning(monkeypatch) -> None:
    monkeypatch.setattr(profile_module, "benchmark_storage_profile", lambda **_: _result())

    sample = run_storage_profile(
        config=StorageProfileConfig.quick(),
        discovery=make_result(),
        sample_id="storage-no-raw",
    )

    assert "raw_output_not_persisted" in sample.quality.warnings
    assert sample.quality.status is SampleQualityStatus.VALID_WITH_WARNINGS


def test_benchmark_failure_creates_invalid_sample(monkeypatch) -> None:
    def fail(**_):
        raise OSError("device unavailable")

    monkeypatch.setattr(profile_module, "benchmark_storage_profile", fail)
    sample = run_storage_profile(
        config=StorageProfileConfig.quick(),
        discovery=make_result(),
        sample_id="storage-failed",
    )

    assert sample.measurements[0].status.value == "failed"
    assert sample.quality.status is SampleQualityStatus.INVALID
    assert sample.quality.errors == ("storage_measurement_failed",)
