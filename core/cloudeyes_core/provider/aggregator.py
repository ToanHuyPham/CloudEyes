"""Build deterministic offline provider analytics bundles."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import UTC, datetime

from ..assessment import build_scorecard
from ..cohorts import build_cohorts
from ..explanation import build_explanations
from ..models import (
    AnalyticsBundle,
    Cohort,
    PriceQuote,
    PricingCommitment,
    PricingOperatingSystem,
    ProviderAnalyticsReport,
    Sample,
    SampleQualityStatus,
)
from ..pricing import build_value_comparisons, match_pricing_evidence
from ..validation import ensure_valid_sample
from .comparison import build_peer_comparisons
from .report import build_provider_reports

ANALYTICS_SCHEMA_VERSION = "1.2.0"


def _analytics_id(provider_id: str, report_id: str) -> str:
    digest = hashlib.sha256(
        f"{ANALYTICS_SCHEMA_VERSION}\n{provider_id}\n{report_id}".encode()
    ).hexdigest()[:16]
    return f"provider-analytics-{digest}"


def build_analytics_bundle(
    samples: tuple[Sample, ...],
    *,
    expected_metrics: tuple[str, ...] = (),
    generated_at: datetime | None = None,
    pricing_quotes: tuple[PriceQuote, ...] = (),
    pricing_commitment: PricingCommitment = PricingCommitment.ON_DEMAND,
    pricing_operating_system: PricingOperatingSystem = PricingOperatingSystem.LINUX,
) -> AnalyticsBundle:
    """Validate samples and create one analytics report per represented provider."""

    generated = generated_at or datetime.now(UTC)
    if generated.tzinfo is None:
        raise ValueError("generated_at must contain timezone information")

    seen_ids: set[str] = set()
    excluded: list[str] = []
    valid_samples: list[Sample] = []
    for sample in samples:
        if sample.sample_id in seen_ids:
            raise ValueError(f"duplicate sample ID: {sample.sample_id}")
        seen_ids.add(sample.sample_id)
        if sample.quality.status is SampleQualityStatus.INVALID:
            excluded.append(sample.sample_id)
            continue
        ensure_valid_sample(sample)
        valid_samples.append(sample)

    excluded_ids = tuple(sorted(excluded))
    cohorts = build_cohorts(tuple(valid_samples))
    reports = build_provider_reports(
        cohorts,
        expected_metrics=expected_metrics,
        generated_at=generated,
    )

    cohorts_by_provider: dict[str, list[Cohort]] = defaultdict(list)
    for cohort in cohorts:
        cohorts_by_provider[cohort.key.provider_id].append(cohort)

    comparisons_by_provider = build_peer_comparisons(cohorts, reports)
    pricing_match = match_pricing_evidence(
        cohorts,
        reports,
        pricing_quotes,
        generated_at=generated,
        commitment=pricing_commitment,
        operating_system=pricing_operating_system,
    )
    value_comparisons_by_provider = build_value_comparisons(
        cohorts,
        reports,
        pricing_match.cohort_evidence,
    )
    pricing_by_provider: dict[str, list] = defaultdict(list)
    for evidence in pricing_match.evidence:
        pricing_by_provider[evidence.provider_id.casefold()].append(evidence)

    analytics_reports: list[ProviderAnalyticsReport] = []
    for report in reports:
        provider_cohorts = tuple(
            sorted(cohorts_by_provider[report.provider_id], key=lambda item: item.key.value)
        )
        peer_comparisons = comparisons_by_provider.get(report.provider_id, ())
        pricing_evidence = tuple(
            sorted(
                pricing_by_provider.get(report.provider_id.casefold(), ()),
                key=lambda item: item.pricing_evidence_id,
            )
        )
        value_comparisons = value_comparisons_by_provider.get(report.provider_id, ())
        scorecard = build_scorecard(
            report,
            provider_cohorts,
            peer_comparisons,
            pricing_evidence,
            value_comparisons,
        )
        analytics_reports.append(
            ProviderAnalyticsReport(
                schema_version=ANALYTICS_SCHEMA_VERSION,
                analytics_id=_analytics_id(report.provider_id, report.report_id),
                generated_at=generated,
                provider_id=report.provider_id,
                provider_name=report.provider_name,
                evidence=report,
                scorecard=scorecard,
                explanations=build_explanations(report, scorecard),
                peer_comparisons=peer_comparisons,
                pricing_evidence=pricing_evidence,
                value_comparisons=value_comparisons,
            )
        )

    analyzed_count = sum(report.evidence.total_samples for report in analytics_reports)
    return AnalyticsBundle(
        schema_version=ANALYTICS_SCHEMA_VERSION,
        generated_at=generated,
        source_sample_count=len(samples),
        analyzed_sample_count=analyzed_count,
        excluded_sample_ids=excluded_ids,
        provider_count=len(analytics_reports),
        providers=tuple(analytics_reports),
        peer_group_count=len(
            {
                item.peer_group_id
                for provider in analytics_reports
                for item in provider.peer_comparisons
            }
        ),
        pricing_quote_count=len(pricing_match.selected_quote_ids),
        normalized_pricing_evidence_count=len(pricing_match.evidence),
        unmatched_pricing_quote_ids=pricing_match.unmatched_quote_ids,
        value_peer_group_count=len(
            {
                item.peer_group_id
                for provider in analytics_reports
                for item in provider.value_comparisons
            }
        ),
    )
