"""Tests for Provider Analytics v1 scorecards and explanations."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

from cloudeyes_core.models import (
    AssessmentDimension,
    AssessmentStatus,
    ConfidenceLevel,
    SampleQuality,
    SampleQualityStatus,
)
from cloudeyes_core.pipeline import analyze_provider_analytics
from cloudeyes_core.serialization import to_primitive

from tests.core_factory import make_sample


def _three_samples(values: tuple[float, float, float]):
    start = datetime(2026, 8, 1, tzinfo=UTC)
    return tuple(
        make_sample(
            f"sample-{index + 1}",
            created_at=start + timedelta(days=index),
            values=(value,),
        )
        for index, value in enumerate(values)
    )


def test_builds_multidimensional_scorecard_without_universal_score() -> None:
    bundle = analyze_provider_analytics(
        _three_samples((99.0, 100.0, 101.0)),
        expected_metrics=("compute.cpu.events_per_second",),
        generated_at=datetime(2026, 8, 6, tzinfo=UTC),
    )

    assert bundle.provider_count == 1
    provider = bundle.providers[0]
    assert provider.scorecard.sample_count == 3
    assert provider.scorecard.coverage_ratio == 1.0
    assert provider.scorecard.successful_measurement_ratio == 1.0
    assert (
        provider.scorecard.dimension(AssessmentDimension.EVIDENCE).level is ConfidenceLevel.MEDIUM
    )
    assert (
        provider.scorecard.dimension(AssessmentDimension.CONSISTENCY).level is ConfidenceLevel.HIGH
    )
    assert (
        provider.scorecard.dimension(AssessmentDimension.RELIABILITY).level is ConfidenceLevel.HIGH
    )
    assert (
        provider.scorecard.dimension(AssessmentDimension.PERFORMANCE).status
        is AssessmentStatus.NOT_ASSESSED
    )
    assert (
        provider.scorecard.dimension(AssessmentDimension.VALUE).status
        is AssessmentStatus.NOT_ASSESSED
    )

    primitive = to_primitive(bundle)
    assert "overall_score" not in primitive["providers"][0]["scorecard"]
    assert any(
        item["code"] == "universal_score_not_calculated"
        for item in primitive["providers"][0]["explanations"]
    )


def test_consistency_is_low_when_metric_dispersion_is_high() -> None:
    provider = analyze_provider_analytics(
        _three_samples((10.0, 100.0, 1000.0)),
        generated_at=datetime(2026, 8, 6, tzinfo=UTC),
    ).providers[0]

    consistency = provider.scorecard.dimension(AssessmentDimension.CONSISTENCY)
    assert consistency.level is ConfidenceLevel.LOW
    assert consistency.evidence_refs[0].endswith(":compute.cpu.events_per_second")


def test_quality_warnings_reduce_reliability_without_claiming_provider_uptime() -> None:
    samples = list(_three_samples((99.0, 100.0, 101.0)))
    samples[1] = replace(
        samples[1],
        quality=SampleQuality(
            SampleQualityStatus.VALID_WITH_WARNINGS,
            warnings=("background_load_detected",),
        ),
    )

    provider = analyze_provider_analytics(
        tuple(samples),
        generated_at=datetime(2026, 8, 6, tzinfo=UTC),
    ).providers[0]
    reliability = provider.scorecard.dimension(AssessmentDimension.RELIABILITY)

    assert reliability.level is ConfidenceLevel.MEDIUM
    assert "samples_with_warnings:1" in reliability.limitations
    assert "uptime" not in reliability.summary.casefold()


def test_single_sample_does_not_claim_high_consistency() -> None:
    provider = analyze_provider_analytics(
        (make_sample("single-sample"),),
        generated_at=datetime(2026, 8, 6, tzinfo=UTC),
    ).providers[0]

    consistency = provider.scorecard.dimension(AssessmentDimension.CONSISTENCY)
    assert consistency.level is ConfidenceLevel.LOW
    assert "coefficient_of_variation_unavailable" in consistency.limitations


def test_invalid_samples_are_excluded_and_reported() -> None:
    valid = make_sample("valid-sample")
    invalid = replace(
        make_sample("invalid-sample"),
        quality=SampleQuality(
            SampleQualityStatus.INVALID,
            errors=("networking_measurement_failed",),
        ),
    )

    bundle = analyze_provider_analytics(
        (valid, invalid),
        generated_at=datetime(2026, 8, 6, tzinfo=UTC),
    )

    assert bundle.source_sample_count == 2
    assert bundle.analyzed_sample_count == 1
    assert bundle.excluded_sample_ids == ("invalid-sample",)
    assert bundle.providers[0].evidence.total_samples == 1
