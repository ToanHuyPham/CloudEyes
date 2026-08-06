"""Build provider-level reports from analyzed cohorts."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import UTC, datetime

from ..assessment import calculate_confidence
from ..cohorts import summarize_cohort
from ..coverage import calculate_coverage
from ..models import Cohort, CohortReport, ConfidenceLevel, ProviderReport

SCHEMA_VERSION = "1.0.0"


def _identifier(prefix: str, parts: tuple[str, ...]) -> str:
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def build_cohort_report(
    cohort: Cohort,
    *,
    expected_metrics: tuple[str, ...] = (),
) -> CohortReport:
    """Create a complete report for one cohort."""

    summary = summarize_cohort(cohort)
    coverage = calculate_coverage(cohort, summary, expected_metrics=expected_metrics)
    confidence = calculate_confidence(summary, coverage)
    sample_ids = tuple(sample.sample_id for sample in cohort.samples)

    return CohortReport(
        cohort_id=_identifier("cohort", (cohort.key.value, *sample_ids)),
        cohort_key=cohort.key.value,
        protocol=cohort.samples[0].protocol,
        started_at=cohort.started_at,
        ended_at=cohort.ended_at,
        sample_count=cohort.sample_count,
        sample_ids=sample_ids,
        coverage=coverage,
        confidence=confidence,
        metrics=summary.metrics,
    )


def build_provider_reports(
    cohorts: tuple[Cohort, ...],
    *,
    expected_metrics: tuple[str, ...] = (),
    generated_at: datetime | None = None,
) -> tuple[ProviderReport, ...]:
    """Create one provider report for each provider represented by the cohorts."""

    generated = generated_at or datetime.now(UTC)
    if generated.tzinfo is None:
        raise ValueError("generated_at must contain timezone information")

    grouped: dict[str, list[Cohort]] = defaultdict(list)
    for cohort in cohorts:
        grouped[cohort.key.provider_id].append(cohort)

    reports: list[ProviderReport] = []
    confidence_order = {
        ConfidenceLevel.LOW: 0,
        ConfidenceLevel.MEDIUM: 1,
        ConfidenceLevel.HIGH: 2,
    }

    for provider_id, provider_cohorts in sorted(grouped.items()):
        ordered_cohorts = tuple(sorted(provider_cohorts, key=lambda item: item.key.value))
        cohort_reports = tuple(
            build_cohort_report(cohort, expected_metrics=expected_metrics)
            for cohort in ordered_cohorts
        )
        overall_confidence = min(
            (item.confidence.overall for item in cohort_reports),
            key=confidence_order.__getitem__,
        )
        gaps = tuple(
            sorted({gap for item in cohort_reports for gap in item.coverage.gaps})
        )
        provider_name = ordered_cohorts[0].provider_name
        report_parts = (
            provider_id,
            *(item.cohort_id for item in cohort_reports),
        )

        reports.append(
            ProviderReport(
                schema_version=SCHEMA_VERSION,
                report_id=_identifier("provider-report", report_parts),
                generated_at=generated,
                provider_id=provider_id,
                provider_name=provider_name,
                total_samples=sum(item.sample_count for item in cohort_reports),
                cohort_count=len(cohort_reports),
                overall_confidence=overall_confidence,
                gaps=gaps,
                cohorts=cohort_reports,
            )
        )

    return tuple(reports)
