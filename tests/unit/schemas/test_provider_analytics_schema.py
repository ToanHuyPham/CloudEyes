"""Schema contract for Provider Analytics v1."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cloudeyes_core.pipeline import analyze_provider_analytics
from cloudeyes_core.serialization import to_primitive
from jsonschema import Draft202012Validator, FormatChecker

from tests.core_factory import make_sample

ROOT = Path(__file__).resolve().parents[3]


def test_provider_analytics_matches_schema() -> None:
    start = datetime(2026, 8, 1, tzinfo=UTC)
    samples = tuple(
        make_sample(
            f"sample-{index + 1}",
            created_at=start + timedelta(days=index),
            values=(value,),
        )
        for index, value in enumerate((99.0, 100.0, 101.0))
    )
    result = analyze_provider_analytics(
        samples,
        expected_metrics=("compute.cpu.events_per_second",),
        generated_at=datetime(2026, 8, 6, tzinfo=UTC),
    )
    schema = json.loads(
        (ROOT / "schemas" / "provider" / "analytics-v1.schema.json").read_text(encoding="utf-8")
    )

    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(
            to_primitive(result)
        ),
        key=lambda error: tuple(str(item) for item in error.path),
    )
    assert not errors, "\n".join(error.message for error in errors)
