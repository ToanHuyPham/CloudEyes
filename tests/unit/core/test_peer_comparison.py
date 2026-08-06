"""Tests for strict compatible peer comparison v1."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest
from cloudeyes_core.models import (
    AssessmentDimension,
    AssessmentStatus,
    ConfidenceLevel,
    MetricDirection,
    PeerComparisonOutcome,
)
from cloudeyes_core.pipeline import analyze_provider_analytics

from tests.core_factory import make_sample

GENERATED_AT = datetime(2026, 8, 6, tzinfo=UTC)


def _provider_sample(
    sample_id: str,
    provider_id: str,
    value: float,
    *,
    provider_name: str | None = None,
    **kwargs,
):
    return make_sample(
        sample_id,
        provider_id=provider_id,
        provider_name=provider_name or provider_id.upper(),
        values=(value,),
        **kwargs,
    )


def _with_direction(sample, direction: MetricDirection):
    measurements = tuple(
        replace(
            measurement,
            metrics=tuple(replace(metric, direction=direction) for metric in measurement.metrics),
        )
        for measurement in sample.measurements
    )
    return replace(sample, measurements=measurements)


def _provider(bundle, provider_id: str):
    return next(item for item in bundle.providers if item.provider_id == provider_id)


def test_higher_is_better_metric_builds_directional_peer_results() -> None:
    bundle = analyze_provider_analytics(
        (
            _provider_sample("alpha-1", "alpha", 120.0),
            _provider_sample("beta-1", "beta", 100.0),
        ),
        generated_at=GENERATED_AT,
    )

    assert bundle.schema_version == "1.2.0"
    assert bundle.peer_group_count == 1

    alpha = _provider(bundle, "alpha")
    beta = _provider(bundle, "beta")
    alpha_comparison = alpha.peer_comparisons[0]
    beta_comparison = beta.peer_comparisons[0]

    assert alpha_comparison.outcome is PeerComparisonOutcome.AHEAD
    assert alpha_comparison.relative_difference_percent == pytest.approx(20.0)
    assert alpha_comparison.peer_provider_ids == ("beta",)
    assert beta_comparison.outcome is PeerComparisonOutcome.BEHIND
    assert beta_comparison.relative_difference_percent == pytest.approx(-16.6666667)

    alpha_performance = alpha.scorecard.dimension(AssessmentDimension.PERFORMANCE)
    beta_performance = beta.scorecard.dimension(AssessmentDimension.PERFORMANCE)
    assert alpha_performance.status is AssessmentStatus.ASSESSED
    assert alpha_performance.level is ConfidenceLevel.HIGH
    assert beta_performance.level is ConfidenceLevel.LOW
    assert "single_peer_baselines:1" in alpha_performance.limitations


def test_lower_is_better_metric_inverts_relative_direction() -> None:
    alpha = _with_direction(
        _provider_sample(
            "alpha-1",
            "alpha",
            80.0,
            metric_name="network.http.ttfb.p50_milliseconds",
            unit="milliseconds",
        ),
        MetricDirection.LOWER_IS_BETTER,
    )
    beta = _with_direction(
        _provider_sample(
            "beta-1",
            "beta",
            100.0,
            metric_name="network.http.ttfb.p50_milliseconds",
            unit="milliseconds",
        ),
        MetricDirection.LOWER_IS_BETTER,
    )

    bundle = analyze_provider_analytics((alpha, beta), generated_at=GENERATED_AT)
    comparison = _provider(bundle, "alpha").peer_comparisons[0]

    assert comparison.direction is MetricDirection.LOWER_IS_BETTER
    assert comparison.relative_difference_percent == pytest.approx(20.0)
    assert comparison.outcome is PeerComparisonOutcome.AHEAD


def test_values_inside_five_percent_band_are_similar() -> None:
    bundle = analyze_provider_analytics(
        (
            _provider_sample("alpha-1", "alpha", 103.0),
            _provider_sample("beta-1", "beta", 100.0),
        ),
        generated_at=GENERATED_AT,
    )

    alpha = _provider(bundle, "alpha")
    comparison = alpha.peer_comparisons[0]
    performance = alpha.scorecard.dimension(AssessmentDimension.PERFORMANCE)
    assert comparison.outcome is PeerComparisonOutcome.SIMILAR
    assert performance.level is ConfidenceLevel.MEDIUM


def test_incompatible_hardware_does_not_create_peer_baseline() -> None:
    bundle = analyze_provider_analytics(
        (
            _provider_sample("alpha-1", "alpha", 120.0, cpu_count=2),
            _provider_sample("beta-1", "beta", 100.0, cpu_count=4),
        ),
        generated_at=GENERATED_AT,
    )

    assert bundle.peer_group_count == 0
    for provider in bundle.providers:
        assert provider.peer_comparisons == ()
        performance = provider.scorecard.dimension(AssessmentDimension.PERFORMANCE)
        assert performance.status is AssessmentStatus.NOT_ASSESSED
        assert "compatible_peer_baseline_required" in performance.limitations


def test_each_provider_has_equal_weight_across_multiple_compatible_cohorts() -> None:
    bundle = analyze_provider_analytics(
        (
            _provider_sample(
                "alpha-plan-a",
                "alpha",
                100.0,
                plan="plan-a",
                region="hanoi-a",
            ),
            _provider_sample(
                "alpha-plan-b",
                "alpha",
                200.0,
                plan="plan-b",
                region="hanoi-b",
            ),
            _provider_sample("beta-1", "beta", 100.0),
        ),
        generated_at=GENERATED_AT,
    )

    alpha_comparison = _provider(bundle, "alpha").peer_comparisons[0]
    beta_comparison = _provider(bundle, "beta").peer_comparisons[0]

    assert alpha_comparison.provider_value == 150.0
    assert len(alpha_comparison.provider_cohort_ids) == 2
    assert alpha_comparison.peer_median == 100.0
    assert beta_comparison.peer_median == 150.0
    assert beta_comparison.peer_provider_count == 1


def test_unknown_geography_is_not_silently_compared() -> None:
    first = replace(
        _provider_sample("alpha-1", "alpha", 120.0),
        provider=replace(
            _provider_sample("alpha-provider", "alpha", 120.0).provider,
            country_code=None,
        ),
    )
    second = replace(
        _provider_sample("beta-1", "beta", 100.0),
        provider=replace(
            _provider_sample("beta-provider", "beta", 100.0).provider,
            country_code=None,
        ),
    )

    bundle = analyze_provider_analytics((first, second), generated_at=GENERATED_AT)
    assert bundle.peer_group_count == 0
