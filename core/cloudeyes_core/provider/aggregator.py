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
    ProviderAnalyticsReport,
    Sample,
    SampleQualityStatus,
)
from ..validation import ensure_valid_sample
from .report import build_provider_reports

ANALYTICS_SCHEMA_VERSION = "1.0.0"


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
) -> AnalyticsBundle:
    """Validate samples and create one analytics report per represented provider."""

    generated = generated_at or datetime.now(UTC)
    if generated.tzinfo is None:
        raise ValueError("generated_at must contain timezone information")

    seen_ids: set[str] = set()
    excluded: list[str] = []
    for sample in samples:
        if sample.sample_id in seen_ids:
            raise ValueError(f"duplicate sample ID: {sample.sample_id}")
        seen_ids.add(sample.sample_id)
        if sample.quality.status is SampleQualityStatus.INVALID:
            excluded.append(sample.sample_id)
            continue
        ensure_valid_sample(sample)

    excluded_ids = tuple(sorted(excluded))
    cohorts = build_cohorts(samples)
    reports = build_provider_reports(
        cohorts,
        expected_metrics=expected_metrics,
        generated_at=generated,
    )

    cohorts_by_provider: dict[str, list[Cohort]] = defaultdict(list)
    for cohort in cohorts:
        cohorts_by_provider[cohort.key.provider_id].append(cohort)

    analytics_reports: list[ProviderAnalyticsReport] = []
    for report in reports:
        provider_cohorts = tuple(
            sorted(cohorts_by_provider[report.provider_id], key=lambda item: item.key.value)
        )
        scorecard = build_scorecard(report, provider_cohorts)
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
    )
