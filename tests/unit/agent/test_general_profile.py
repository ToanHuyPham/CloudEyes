"""Tests for the complete General Profile v1."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from cloudeyes_agent.profiles.general import (
    GeneralProfileConfig,
    benchmark_cpu,
    benchmark_memory,
    benchmark_storage,
    run_general_profile,
)
from cloudeyes_agent.profiles.general import profile as profile_module
from cloudeyes_core.models import Metric, MetricDirection, SampleQualityStatus
from cloudeyes_core.validation import validate_sample

from tests.unit.agent.test_discovery_models import make_result


def _timer() -> Callable[[], float]:
    values = iter((10.0, 11.0))
    return lambda: next(values)


def _metric(name: str) -> tuple[Metric, ...]:
    return (
        Metric(
            name=name,
            value=100.0,
            unit="mib_per_second",
            direction=MetricDirection.HIGHER_IS_BETTER,
        ),
    )


def test_default_config_is_bounded_and_fingerprint_is_stable() -> None:
    first = GeneralProfileConfig()
    second = GeneralProfileConfig()

    assert first.fingerprint == second.fingerprint
    assert len(first.fingerprint) == 64
    assert first.storage_block_bytes * first.storage_iterations <= 512 * 1024 * 1024


def test_config_rejects_unbounded_storage_workload() -> None:
    with pytest.raises(ValueError, match="512 MiB"):
        GeneralProfileConfig(
            storage_block_bytes=64 * 1024 * 1024,
            storage_iterations=9,
        )


def test_config_rejects_unbounded_cpu_workload() -> None:
    with pytest.raises(ValueError, match="1 GiB"):
        GeneralProfileConfig(
            cpu_block_bytes=1024 * 1024,
            cpu_iterations=1025,
        )


def test_cpu_benchmark_returns_normalized_metric() -> None:
    metric = benchmark_cpu(block_bytes=64, iterations=2, timer=_timer())[0]

    assert metric.name == "compute.cpu.sha256_mib_per_second"
    assert metric.value > 0
    assert metric.direction is MetricDirection.HIGHER_IS_BETTER


def test_memory_benchmark_returns_normalized_metric() -> None:
    metric = benchmark_memory(block_bytes=64, iterations=2, timer=_timer())[0]

    assert metric.name == "memory.copy.mib_per_second"
    assert metric.value > 0


def test_storage_benchmark_uses_temporary_file(tmp_path) -> None:
    metrics = benchmark_storage(
        block_bytes=1024,
        iterations=2,
        fsync=False,
        work_dir=tmp_path,
    )

    assert {metric.name for metric in metrics} == {
        "storage.sequential_read.mib_per_second",
        "storage.sequential_write.mib_per_second",
    }
    assert all(metric.value > 0 for metric in metrics)
    assert list(tmp_path.iterdir()) == []


def test_profile_builds_a_valid_core_sample(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        profile_module,
        "benchmark_cpu",
        lambda **_: _metric("compute.cpu.sha256_mib_per_second"),
    )
    monkeypatch.setattr(
        profile_module,
        "benchmark_memory",
        lambda **_: _metric("memory.copy.mib_per_second"),
    )
    monkeypatch.setattr(
        profile_module,
        "benchmark_storage",
        lambda **_: _metric("storage.sequential_write.mib_per_second"),
    )
    fixed_time = datetime(2026, 8, 6, 13, 0, tzinfo=UTC)

    sample = run_general_profile(
        config=GeneralProfileConfig.quick(),
        discovery=make_result(),
        sample_id="general-test",
        work_dir=tmp_path,
        country_code="VN",
        product="Cloud Server",
        plan="2-vcpu-4gb",
        region="hanoi",
        zone="zone-1",
        clock=lambda: fixed_time,
    )

    assert sample.protocol.profile == "general"
    assert sample.protocol.version == "1.0.0"
    assert len(sample.measurements) == 3
    assert sample.quality.status is SampleQualityStatus.VALID
    assert validate_sample(sample).valid is True


def test_disabled_storage_is_explicitly_skipped(monkeypatch) -> None:
    monkeypatch.setattr(
        profile_module,
        "benchmark_cpu",
        lambda **_: _metric("compute.cpu.sha256_mib_per_second"),
    )
    monkeypatch.setattr(
        profile_module,
        "benchmark_memory",
        lambda **_: _metric("memory.copy.mib_per_second"),
    )

    sample = run_general_profile(
        config=GeneralProfileConfig.quick(include_storage=False),
        discovery=make_result(),
        sample_id="general-no-storage",
        country_code="VN",
    )

    assert sample.measurements[-1].status.value == "skipped"
    assert "measurement_skipped:python-sequential-io" in sample.quality.warnings
    assert sample.quality.status is SampleQualityStatus.VALID_WITH_WARNINGS


def test_benchmark_failure_is_preserved_in_sample(monkeypatch) -> None:
    def fail(**_):
        raise OSError("benchmark unavailable")

    monkeypatch.setattr(profile_module, "benchmark_cpu", fail)
    monkeypatch.setattr(
        profile_module,
        "benchmark_memory",
        lambda **_: _metric("memory.copy.mib_per_second"),
    )
    monkeypatch.setattr(
        profile_module,
        "benchmark_storage",
        lambda **_: _metric("storage.sequential_write.mib_per_second"),
    )

    sample = run_general_profile(
        config=GeneralProfileConfig.quick(),
        discovery=make_result(),
        sample_id="general-partial-failure",
        country_code="VN",
    )

    assert sample.measurements[0].status.value == "failed"
    assert sample.measurements[0].error == "OSError: benchmark failed"
    assert sample.quality.status is SampleQualityStatus.VALID_WITH_WARNINGS
