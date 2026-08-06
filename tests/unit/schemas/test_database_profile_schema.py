"""Schema contract tests for Database Profile output."""

from __future__ import annotations

import json
from pathlib import Path

from cloudeyes_agent.profiles.database import DatabaseProfileConfig, run_database_profile
from cloudeyes_core.serialization import to_primitive
from jsonschema import Draft202012Validator, FormatChecker

from tests.unit.agent.test_discovery_models import make_result

ROOT = Path(__file__).resolve().parents[3]


def _validator() -> Draft202012Validator:
    schema = json.loads((ROOT / "schemas/sample/sample.schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=FormatChecker())


def test_database_profile_sample_matches_core_schema(tmp_path) -> None:
    sample = run_database_profile(
        config=DatabaseProfileConfig.quick(),
        discovery=make_result(),
        sample_id="database-schema-test",
        work_dir=tmp_path / "work",
        raw_output_dir=tmp_path / "raw",
        country_code="VN",
    )

    _validator().validate(to_primitive(sample))


def test_database_profile_example_matches_core_schema() -> None:
    example = json.loads(
        (ROOT / "examples/database-profile-sample.json").read_text(encoding="utf-8")
    )

    _validator().validate(example)
