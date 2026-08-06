"""Tests for immutable Core Foundation models."""

from datetime import UTC, datetime

import pytest

from cloudeyes_core.models import (
    Confidence,
    ConfidenceLevel,
    MachineIdentity,
    Metric,
    ProviderIdentity,
    SampleQuality,
    SampleQualityStatus,
)


def test_provider_country_code_is_normalized() -> None:
    assert ProviderIdentity("provider", "Provider", "vn").country_code == "VN"


def test_country_code_rejects_invalid_value() -> None:
    with pytest.raises(ValueError, match="2-letter"):
        ProviderIdentity("provider", "Provider", "VNM")


def test_machine_requires_positive_resources() -> None:
    with pytest.raises(ValueError, match="cpu_count"):
        MachineIdentity("vm", 0, 1024, "x86_64")


def test_metric_rejects_non_finite_values() -> None:
    with pytest.raises(ValueError, match="finite"):
        Metric("cpu.score", float("inf"), "score")


def test_invalid_quality_requires_error() -> None:
    with pytest.raises(ValueError, match="at least one error"):
        SampleQuality(SampleQualityStatus.INVALID)


def test_confidence_overall_uses_lowest_dimension() -> None:
    confidence = Confidence(
        measurement=ConfidenceLevel.HIGH,
        statistical=ConfidenceLevel.MEDIUM,
        coverage=ConfidenceLevel.LOW,
    )
    assert confidence.overall is ConfidenceLevel.LOW


def test_naive_datetime_is_rejected_by_factory_model() -> None:
    from tests.core_factory import make_sample

    with pytest.raises(ValueError, match="timezone"):
        make_sample(created_at=datetime(2026, 8, 1))


def test_utc_datetime_is_accepted() -> None:
    from tests.core_factory import make_sample

    sample = make_sample(created_at=datetime(2026, 8, 1, tzinfo=UTC))
    assert sample.created_at.tzinfo is UTC
