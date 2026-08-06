"""Tests for Normalized Pricing v1."""

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
    PricingSourceTier,
    ValueIndexDefinition,
)
from cloudeyes_core.pipeline import analyze_provider_analytics
from cloudeyes_core.pricing import normalize_hourly_usd, value_index

from tests.core_factory import make_price_quote, make_sample

GENERATED_AT = datetime(2026, 8, 6, tzinfo=UTC)


def _provider(bundle, provider_id: str):
    return next(item for item in bundle.providers if item.provider_id == provider_id)


def test_normalizes_monthly_foreign_currency_to_hourly_usd() -> None:
    quote = make_price_quote(
        "monthly-eur",
        "alpha",
        amount=73.0,
        currency="EUR",
        billing_period="month",
        billing_period_hours=730.0,
        fx_to_usd=1.1,
    )

    assert normalize_hourly_usd(quote) == pytest.approx(0.11)


def test_value_index_keeps_larger_values_better_for_both_directions() -> None:
    higher = value_index(100.0, 0.1, MetricDirection.HIGHER_IS_BETTER)
    lower = value_index(10.0, 0.1, MetricDirection.LOWER_IS_BETTER)

    assert higher == pytest.approx((1000.0, ValueIndexDefinition.METRIC_PER_USD_HOUR))
    assert lower is not None
    assert lower[0] == pytest.approx(1.0)
    assert lower[1] is ValueIndexDefinition.INVERSE_METRIC_USD_HOUR


def test_specific_quote_wins_over_provider_wide_quote() -> None:
    sample = make_sample("alpha-1", provider_id="alpha", provider_name="Alpha")
    broad = make_price_quote(
        "alpha-broad",
        "alpha",
        amount=0.2,
        region=None,
        zone=None,
    )
    specific = make_price_quote("alpha-specific", "alpha", amount=0.1)

    provider = analyze_provider_analytics(
        (sample,),
        generated_at=GENERATED_AT,
        pricing_quotes=(broad, specific),
    ).providers[0]

    assert len(provider.pricing_evidence) == 1
    assert provider.pricing_evidence[0].quote_id == "alpha-specific"
    assert provider.pricing_evidence[0].hourly_usd == pytest.approx(0.1)


def test_quote_must_cover_entire_cohort_time_window() -> None:
    samples = (
        make_sample("alpha-1", provider_id="alpha", created_at=datetime(2026, 8, 1, tzinfo=UTC)),
        make_sample("alpha-2", provider_id="alpha", created_at=datetime(2026, 8, 3, tzinfo=UTC)),
    )
    quote = make_price_quote(
        "alpha-expired",
        "alpha",
        valid_until=datetime(2026, 8, 2, tzinfo=UTC),
    )

    bundle = analyze_provider_analytics(
        samples,
        generated_at=GENERATED_AT,
        pricing_quotes=(quote,),
    )

    assert bundle.normalized_pricing_evidence_count == 0
    assert bundle.unmatched_pricing_quote_ids == ("alpha-expired",)
    value = bundle.providers[0].scorecard.dimension(AssessmentDimension.VALUE)
    assert value.status is AssessmentStatus.NOT_ASSESSED
    assert "normalized_pricing_required" in value.limitations


def test_ambiguous_top_ranked_quotes_stop_analysis() -> None:
    sample = make_sample("alpha-1", provider_id="alpha")
    first = make_price_quote("alpha-a", "alpha", amount=0.1)
    second = make_price_quote("alpha-b", "alpha", amount=0.2)

    with pytest.raises(ValueError, match="ambiguous pricing quotes"):
        analyze_provider_analytics(
            (sample,),
            generated_at=GENERATED_AT,
            pricing_quotes=(first, second),
        )


def test_normalized_pricing_builds_value_comparisons_and_assesses_value() -> None:
    samples = (
        make_sample(
            "alpha-1",
            provider_id="alpha",
            provider_name="Alpha Cloud",
            values=(120.0,),
        ),
        make_sample(
            "beta-1",
            provider_id="beta",
            provider_name="Beta Cloud",
            values=(100.0,),
        ),
        make_sample(
            "gamma-1",
            provider_id="gamma",
            provider_name="Gamma Cloud",
            values=(105.0,),
        ),
    )
    quotes = (
        make_price_quote("alpha-price", "alpha", amount=0.12),
        make_price_quote("beta-price", "beta", amount=0.08),
        make_price_quote("gamma-price", "gamma", amount=0.09),
    )

    bundle = analyze_provider_analytics(
        samples,
        generated_at=GENERATED_AT,
        pricing_quotes=quotes,
    )

    assert bundle.schema_version == "1.2.0"
    assert bundle.pricing_quote_count == 3
    assert bundle.normalized_pricing_evidence_count == 3
    assert bundle.value_peer_group_count == 1
    assert bundle.unmatched_pricing_quote_ids == ()

    alpha = _provider(bundle, "alpha")
    beta = _provider(bundle, "beta")
    gamma = _provider(bundle, "gamma")
    assert alpha.peer_comparisons[0].outcome is PeerComparisonOutcome.AHEAD
    assert beta.peer_comparisons[0].outcome is PeerComparisonOutcome.BEHIND
    assert alpha.value_comparisons[0].outcome is PeerComparisonOutcome.BEHIND
    assert beta.value_comparisons[0].outcome is PeerComparisonOutcome.AHEAD
    assert gamma.value_comparisons[0].outcome is PeerComparisonOutcome.SIMILAR
    assert alpha.value_comparisons[0].provider_value_index == pytest.approx(1000.0)
    assert beta.value_comparisons[0].provider_value_index == pytest.approx(1250.0)

    alpha_value = alpha.scorecard.dimension(AssessmentDimension.VALUE)
    beta_value = beta.scorecard.dimension(AssessmentDimension.VALUE)
    gamma_value = gamma.scorecard.dimension(AssessmentDimension.VALUE)
    assert alpha_value.status is AssessmentStatus.ASSESSED
    assert alpha_value.level is ConfidenceLevel.LOW
    assert beta_value.level is ConfidenceLevel.HIGH
    assert gamma_value.level is ConfidenceLevel.MEDIUM


def test_manual_pricing_caps_value_comparison_confidence() -> None:
    samples = (
        make_sample("alpha-1", provider_id="alpha", values=(120.0,)),
        make_sample("beta-1", provider_id="beta", values=(100.0,)),
    )
    quotes = (
        make_price_quote(
            "alpha-price",
            "alpha",
            source_tier=PricingSourceTier.MANUAL,
        ),
        make_price_quote("beta-price", "beta"),
    )

    bundle = analyze_provider_analytics(
        samples,
        generated_at=GENERATED_AT,
        pricing_quotes=quotes,
    )

    assert _provider(bundle, "alpha").value_comparisons[0].confidence is ConfidenceLevel.LOW


def test_lower_is_better_value_comparison_uses_inverse_cost_index() -> None:
    def lower_sample(sample_id: str, provider_id: str, value: float):
        sample = make_sample(
            sample_id,
            provider_id=provider_id,
            values=(value,),
            metric_name="network.http.ttfb.p50_milliseconds",
            unit="milliseconds",
        )
        return replace(
            sample,
            measurements=tuple(
                replace(
                    measurement,
                    metrics=tuple(
                        replace(metric, direction=MetricDirection.LOWER_IS_BETTER)
                        for metric in measurement.metrics
                    ),
                )
                for measurement in sample.measurements
            ),
        )

    samples = (lower_sample("alpha-1", "alpha", 80.0), lower_sample("beta-1", "beta", 100.0))
    quotes = (
        make_price_quote("alpha-price", "alpha", amount=0.1),
        make_price_quote("beta-price", "beta", amount=0.1),
    )
    bundle = analyze_provider_analytics(
        samples,
        generated_at=GENERATED_AT,
        pricing_quotes=quotes,
    )

    comparison = _provider(bundle, "alpha").value_comparisons[0]
    assert comparison.index_definition is ValueIndexDefinition.INVERSE_METRIC_USD_HOUR
    assert comparison.outcome is PeerComparisonOutcome.AHEAD
    assert comparison.relative_difference_percent == pytest.approx(25.0)
