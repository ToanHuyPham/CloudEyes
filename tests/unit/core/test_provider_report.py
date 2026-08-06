"""Tests for provider-level report generation."""

from datetime import UTC, datetime, timedelta

from cloudeyes_core.cohorts import build_cohorts
from cloudeyes_core.models import ConfidenceLevel
from cloudeyes_core.provider import build_provider_reports
from tests.core_factory import make_sample


def test_multiple_cohorts_create_one_provider_report() -> None:
    cohorts = build_cohorts((make_sample("a", region="hanoi"), make_sample("b", region="danang")))
    reports = build_provider_reports(cohorts, generated_at=datetime(2026, 8, 8, tzinfo=UTC))
    assert len(reports) == 1
    assert reports[0].cohort_count == 2
    assert reports[0].total_samples == 2


def test_multiple_providers_create_multiple_reports() -> None:
    cohorts = build_cohorts((make_sample("a"), make_sample("b", provider_id="other", provider_name="Other")))
    assert len(build_provider_reports(cohorts)) == 2


def test_report_identifier_is_deterministic() -> None:
    cohorts = build_cohorts((make_sample("a"),))
    first = build_provider_reports(cohorts)[0]
    second = build_provider_reports(cohorts)[0]
    assert first.report_id == second.report_id


def test_report_overall_confidence_is_conservative() -> None:
    start = datetime(2026, 8, 1, tzinfo=UTC)
    samples = tuple(make_sample(f"s-{index}", created_at=start + timedelta(days=index), values=(100.0,)) for index in range(3))
    report = build_provider_reports(build_cohorts(samples))[0]
    assert report.overall_confidence in {ConfidenceLevel.MEDIUM, ConfidenceLevel.HIGH}
