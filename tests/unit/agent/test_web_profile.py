"""Tests for CloudEyes Web Profile v1."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest
from cloudeyes_agent.profiles.web import (
    NetworkScope,
    WebProfileConfig,
    WebSafetyError,
    benchmark_web_profile,
    run_web_profile,
)
from cloudeyes_agent.storage import load_raw_output
from cloudeyes_core.models import SampleQualityStatus
from cloudeyes_core.validation import validate_sample

from tests.unit.agent.test_discovery_models import make_result
from tests.web_test_server import local_web_endpoint


def test_web_config_rejects_credentials_and_unbounded_concurrency() -> None:
    with pytest.raises(ValueError, match="credentials"):
        WebProfileConfig(target_url="https://user:secret@example.com/")

    with pytest.raises(ValueError, match="concurrency"):
        WebProfileConfig(request_count=2, concurrency=3)


def test_web_config_fingerprint_tracks_workload() -> None:
    base = WebProfileConfig.quick()

    assert base.fingerprint == WebProfileConfig.quick().fingerprint
    assert base.fingerprint != replace(base, request_count=5).fingerprint


def test_web_benchmark_produces_metrics_and_sanitized_evidence() -> None:
    with local_web_endpoint() as base_url:
        config = WebProfileConfig.quick(
            target_url=f"{base_url}/ok?token=do-not-store",
            scope=NetworkScope.PRIVATE,
        )
        result = benchmark_web_profile(config=config)

    metrics = {metric.name: metric.value for metric in result.metrics}
    assert metrics["web.http.error_rate.percent"] == 0.0
    assert metrics["web.http.successful_requests_per_second"] > 0
    assert metrics["web.http.total_latency.p95_milliseconds"] > 0
    assert result.evidence["summary"]["successful_requests"] == 6
    assert result.evidence["target"]["query_present"] is True
    assert "do-not-store" not in json.dumps(result.evidence)
    assert "127.0.0.1" in result.evidence["target"]["origin"]
    assert all("response_body" not in item for item in result.evidence["requests"])


def test_web_benchmark_reports_partial_failures() -> None:
    with local_web_endpoint() as base_url:
        config = WebProfileConfig(
            target_url=f"{base_url}/flaky",
            scope=NetworkScope.PRIVATE,
            request_count=6,
            concurrency=2,
            warmup_requests=0,
            max_response_bytes=128 * 1024,
        )
        result = benchmark_web_profile(config=config)

    metrics = {metric.name: metric.value for metric in result.metrics}
    assert metrics["web.http.error_rate.percent"] > 0
    assert "web_partial_request_failures" in result.warnings
    assert "web_server_error_responses_observed" in result.warnings


def test_web_benchmark_rejects_private_target_in_public_scope() -> None:
    with local_web_endpoint() as base_url:
        config = WebProfileConfig.quick(target_url=f"{base_url}/ok")
        with pytest.raises(WebSafetyError):
            benchmark_web_profile(config=config)


def test_web_benchmark_rejects_all_failed_requests() -> None:
    with local_web_endpoint() as base_url:
        config = WebProfileConfig(
            target_url=f"{base_url}/error",
            scope=NetworkScope.PRIVATE,
            request_count=3,
            concurrency=1,
            warmup_requests=0,
            max_response_bytes=128 * 1024,
        )
        with pytest.raises(OSError, match="all bounded web requests failed"):
            benchmark_web_profile(config=config)


def test_web_benchmark_records_truncation_without_storing_body() -> None:
    with local_web_endpoint() as base_url:
        config = WebProfileConfig(
            target_url=f"{base_url}/large",
            scope=NetworkScope.PRIVATE,
            request_count=2,
            concurrency=1,
            warmup_requests=0,
            max_response_bytes=4 * 1024,
        )
        result = benchmark_web_profile(config=config)

    assert "web_response_body_truncated" in result.warnings
    assert result.evidence["summary"]["response_bytes"] == 8 * 1024


def test_web_profile_builds_valid_sample_and_raw_evidence(tmp_path) -> None:
    with local_web_endpoint() as base_url:
        sample = run_web_profile(
            config=WebProfileConfig.quick(
                target_url=f"{base_url}/ok",
                scope=NetworkScope.PRIVATE,
            ),
            discovery=make_result(),
            sample_id="web-unit-test",
            raw_output_dir=tmp_path / "raw",
            country_code="VN",
        )

    assert sample.protocol.profile == "web"
    assert sample.quality.status is SampleQualityStatus.VALID
    assert validate_sample(sample).valid is True
    raw_path = sample.measurements[0].raw_output_path
    assert raw_path is not None
    assert load_raw_output(raw_path)["profile"] == "web"


def test_web_evidence_does_not_persist_resolved_addresses() -> None:
    with local_web_endpoint() as base_url:
        config = WebProfileConfig.quick(
            target_url=f"{base_url}/ok",
            scope=NetworkScope.PRIVATE,
        )
        result = benchmark_web_profile(config=config)

    request_evidence = json.dumps(result.evidence["requests"])
    assert "127.0.0.1" not in request_evidence
    assert result.evidence["target"]["resolved_address_families"] == ("ipv4",)
