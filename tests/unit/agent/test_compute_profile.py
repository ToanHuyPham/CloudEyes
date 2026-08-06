"""Tests for the complete Compute Profile v1."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from cloudeyes_agent.profiles.compute import (
    ComputeBenchmarkResult,
    ComputeProfileConfig,
    benchmark_compute_profile,
    run_compute_profile,
)
from cloudeyes_agent.profiles.compute import profile as profile_module
from cloudeyes_core.models import Metric, MetricDirection, SampleQualityStatus
from cloudeyes_core.validation import validate_sample

from tests.unit.agent.test_discovery_models import make_result


def _result(*, warnings: tuple[str, ...] = ()) -> ComputeBenchmarkResult:
    return ComputeBenchmarkResult(
        metrics=(
            Metric(
                name="compute.integer.single_core.iterations_per_second",
                value=1000.0,
                unit="iterations_per_second",
                direction=MetricDirection.HIGHER_IS_BETTER,
            ),
        ),
        evidence={"schema_version": "1.0.0", "profile": "compute"},
        warnings=warnings,
    )


def test_default_config_is_bounded_and_fingerprint_is_stable() -> None:
    first = ComputeProfileConfig()
    second = ComputeProfileConfig()

    assert first.fingerprint == second.fingerprint
    assert len(first.fingerprint) == 64
    assert first.max_auto_workers <= 4
    assert first.sha256_block_bytes * first.sha256_iterations <= 4 * 1024**3


def test_config_rejects_unsafe_worker_count_and_timeout() -> None:
    with pytest.raises(ValueError, match="workers"):
        ComputeProfileConfig(workers=65)
    with pytest.raises(ValueError, match="worker_timeout_seconds"):
        ComputeProfileConfig(worker_timeout_seconds=0.5)


def test_quick_benchmark_returns_all_metrics_and_evidence() -> None:
    result = benchmark_compute_profile(config=ComputeProfileConfig.quick())

    assert {metric.name for metric in result.metrics} == {
        "compute.compression.single_core.mib_per_second",
        "compute.concurrency.scaling_ratio",
        "compute.concurrency.worker_efficiency_percent",
        "compute.floating_point.single_core.iterations_per_second",
        "compute.integer.multi_core.iterations_per_second",
        "compute.integer.single_core.iterations_per_second",
        "compute.sha256.single_core.mib_per_second",
    }
    assert all(metric.value > 0 for metric in result.metrics)
    assert result.evidence["profile"] == "compute"
    assert result.evidence["execution"]["resolved_workers"] >= 1
    assert result.evidence["verification"]["sha256_checksums"]


def test_single_worker_mode_is_explicit_warning() -> None:
    result = benchmark_compute_profile(config=ComputeProfileConfig.quick(workers=1))

    assert "compute_single_worker_only" in result.warnings
    assert result.evidence["execution"]["resolved_workers"] == 1


def test_profile_builds_valid_sample_and_raw_evidence(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(profile_module, "benchmark_compute_profile", lambda **_: _result())
    fixed_time = datetime(2026, 8, 6, 15, 0, tzinfo=UTC)

    sample = run_compute_profile(
        config=ComputeProfileConfig.quick(workers=1),
        discovery=make_result(),
        sample_id="compute-test",
        raw_output_dir=tmp_path / "raw",
        country_code="VN",
        product="Cloud VM",
        plan="general-purpose",
        region="asia-southeast1",
        zone="asia-southeast1-a",
        clock=lambda: fixed_time,
    )

    assert sample.protocol.profile == "compute"
    assert sample.measurements[0].raw_output_path is not None
    assert sample.quality.status is SampleQualityStatus.VALID
    assert validate_sample(sample).valid is True
    assert (tmp_path / "raw" / "compute-test-compute.json").exists()


def test_profile_propagates_benchmark_warnings(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        profile_module,
        "benchmark_compute_profile",
        lambda **_: _result(warnings=("compute_workers_auto_capped",)),
    )

    sample = run_compute_profile(
        config=ComputeProfileConfig.quick(),
        discovery=make_result(),
        sample_id="compute-warning",
        raw_output_dir=tmp_path / "raw",
    )

    assert "compute_workers_auto_capped" in sample.quality.warnings
    assert sample.quality.status is SampleQualityStatus.VALID_WITH_WARNINGS


def test_benchmark_failure_creates_invalid_sample(monkeypatch) -> None:
    def fail(**_):
        raise RuntimeError("worker failed")

    monkeypatch.setattr(profile_module, "benchmark_compute_profile", fail)
    sample = run_compute_profile(
        config=ComputeProfileConfig.quick(),
        discovery=make_result(),
        sample_id="compute-failed",
    )

    assert sample.measurements[0].status.value == "failed"
    assert sample.quality.status is SampleQualityStatus.INVALID
    assert sample.quality.errors == ("compute_measurement_failed",)
