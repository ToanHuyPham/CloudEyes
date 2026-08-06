"""Tests for the complete Networking Profile v1."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from cloudeyes_agent.profiles.networking import (
    NetworkingBenchmarkResult,
    NetworkingProfileConfig,
    NetworkingSafetyError,
    NetworkScope,
    benchmark_networking_profile,
    parse_packet_loss,
    run_networking_profile,
)
from cloudeyes_agent.profiles.networking import profile as profile_module
from cloudeyes_core.models import Metric, MetricDirection, SampleQualityStatus
from cloudeyes_core.validation import validate_sample

from tests.network_test_server import local_network_endpoint
from tests.unit.agent.test_discovery_models import make_result


def _result(*, warnings: tuple[str, ...] = ()) -> NetworkingBenchmarkResult:
    return NetworkingBenchmarkResult(
        metrics=(
            Metric(
                name="network.tcp.connect.p50_milliseconds",
                value=1.0,
                unit="milliseconds",
                direction=MetricDirection.LOWER_IS_BETTER,
            ),
        ),
        evidence={"schema_version": "1.0.0", "profile": "networking"},
        warnings=warnings,
    )


def test_default_config_is_bounded_and_fingerprint_is_stable() -> None:
    first = NetworkingProfileConfig()
    second = NetworkingProfileConfig()

    assert first.fingerprint == second.fingerprint
    assert len(first.fingerprint) == 64
    assert first.download_limit_bytes <= 64 * 1024 * 1024
    assert first.upload_bytes <= 16 * 1024 * 1024


def test_config_rejects_credentials_and_unsupported_scheme() -> None:
    with pytest.raises(ValueError, match="credentials"):
        NetworkingProfileConfig(target_url="https://user:secret@example.com/")
    with pytest.raises(ValueError, match="http or https"):
        NetworkingProfileConfig(target_url="ftp://example.com/file")


def test_quick_benchmark_runs_against_explicit_private_endpoint() -> None:
    with local_network_endpoint() as (download_url, upload_url):
        result = benchmark_networking_profile(
            config=NetworkingProfileConfig.quick(
                target_url=download_url,
                upload_url=upload_url,
                scope=NetworkScope.PRIVATE,
            )
        )

    names = {metric.name for metric in result.metrics}
    assert "network.dns.lookup.p50_milliseconds" in names
    assert "network.tcp.connect.p50_milliseconds" in names
    assert "network.http.ttfb.p50_milliseconds" in names
    assert "network.download.mib_per_second" in names
    assert "network.upload.mib_per_second" in names
    assert "network.http.request_loss_percent" in names
    assert "network.tls.handshake.p50_milliseconds" not in names
    assert result.evidence["target"]["origin"].startswith("http://127.0.0.1:")
    assert result.evidence["configuration"]["target_url"] is None
    assert result.evidence["download_error_types"] == []


def test_public_scope_rejects_loopback_target() -> None:
    with local_network_endpoint() as (download_url, _):
        config = NetworkingProfileConfig.quick(
            target_url=download_url,
            scope=NetworkScope.PUBLIC,
        )
        with pytest.raises(NetworkingSafetyError, match="disallowed"):
            benchmark_networking_profile(config=config)


def test_packet_loss_parser_covers_linux_and_windows() -> None:
    assert parse_packet_loss("4 packets transmitted, 3 received, 25% packet loss") == 25.0
    assert parse_packet_loss("Packets: Sent = 4, Received = 4, Lost = 0 (0% loss)") == 0.0
    assert parse_packet_loss("unrecognized output") is None


def test_profile_builds_valid_sample_and_raw_evidence(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(profile_module, "benchmark_networking_profile", lambda **_: _result())
    fixed_time = datetime(2026, 8, 6, 14, 0, tzinfo=UTC)

    sample = run_networking_profile(
        config=NetworkingProfileConfig.quick(),
        discovery=make_result(),
        sample_id="networking-test",
        raw_output_dir=tmp_path / "raw",
        country_code="VN",
        product="Cloud VM",
        plan="general-purpose",
        region="asia-southeast1",
        zone="asia-southeast1-a",
        clock=lambda: fixed_time,
    )

    assert sample.protocol.profile == "networking"
    assert sample.measurements[0].raw_output_path is not None
    assert sample.quality.status is SampleQualityStatus.VALID
    assert validate_sample(sample).valid is True
    assert (tmp_path / "raw" / "networking-test-networking.json").exists()


def test_profile_propagates_benchmark_warnings(monkeypatch) -> None:
    monkeypatch.setattr(
        profile_module,
        "benchmark_networking_profile",
        lambda **_: _result(warnings=("upload_target_not_configured",)),
    )

    sample = run_networking_profile(
        config=NetworkingProfileConfig.quick(),
        discovery=make_result(),
        sample_id="networking-warning",
        raw_output_dir="data/raw",
    )

    assert "upload_target_not_configured" in sample.quality.warnings
    assert sample.quality.status is SampleQualityStatus.VALID_WITH_WARNINGS


def test_benchmark_failure_creates_invalid_sample(monkeypatch) -> None:
    def fail(**_):
        raise OSError("endpoint unavailable")

    monkeypatch.setattr(profile_module, "benchmark_networking_profile", fail)
    sample = run_networking_profile(
        config=NetworkingProfileConfig.quick(),
        discovery=make_result(),
        sample_id="networking-failed",
    )

    assert sample.measurements[0].status.value == "failed"
    assert sample.quality.status is SampleQualityStatus.INVALID
    assert sample.quality.errors == ("networking_measurement_failed",)
