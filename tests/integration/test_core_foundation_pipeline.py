"""End-to-end test for the complete Core Foundation flow."""

import json
from datetime import UTC, datetime, timedelta

from cloudeyes_core.pipeline import analyze_repository
from cloudeyes_core.repository import JsonSampleRepository
from cloudeyes_core.serialization import dump
from tests.core_factory import make_sample


def test_repository_to_provider_report_json(tmp_path) -> None:
    repository = JsonSampleRepository(tmp_path / "samples")
    start = datetime(2026, 8, 1, tzinfo=UTC)

    for index, value in enumerate((99.0, 100.0, 101.0)):
        repository.save(
            make_sample(
                f"sample-{index + 1:03d}",
                created_at=start + timedelta(days=index),
                values=(value,),
            )
        )

    reports = analyze_repository(
        repository,
        expected_metrics=("compute.cpu.events_per_second",),
        generated_at=datetime(2026, 8, 8, tzinfo=UTC),
    )
    assert len(reports) == 1
    report = reports[0]
    assert report.total_samples == 3
    assert report.cohort_count == 1
    assert report.cohorts[0].coverage.metric_ratio == 1.0
    assert report.cohorts[0].metrics[0].statistics.median == 100.0

    output = dump(report, tmp_path / "reports" / "provider-report.json")
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["schema_version"] == "1.0.0"
    assert data["provider_id"] == "viettel-cloud"
    assert data["cohorts"][0]["confidence"]["measurement"] == "high"
