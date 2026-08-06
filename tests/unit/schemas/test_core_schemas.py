"""Contract tests for Core Foundation JSON schemas."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from cloudeyes_core.pipeline import analyze_samples
from cloudeyes_core.serialization import to_primitive
from tests.core_factory import make_sample

ROOT = Path(__file__).resolve().parents[3]


def _schema(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_sample_matches_schema() -> None:
    validator = Draft202012Validator(_schema("schemas/sample/sample.schema.json"), format_checker=FormatChecker())
    validator.validate(to_primitive(make_sample()))


def test_provider_report_matches_schema() -> None:
    start = datetime(2026, 8, 1, tzinfo=UTC)
    samples = tuple(make_sample(f"sample-{index}", created_at=start + timedelta(days=index)) for index in range(3))
    report = analyze_samples(
        samples,
        expected_metrics=("compute.cpu.events_per_second",),
        generated_at=datetime(2026, 8, 8, tzinfo=UTC),
    )[0]
    validator = Draft202012Validator(_schema("schemas/report/provider-report.schema.json"), format_checker=FormatChecker())
    validator.validate(to_primitive(report))
