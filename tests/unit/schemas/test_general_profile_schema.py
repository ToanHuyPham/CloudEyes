"""Schema contract test for General Profile output."""

from __future__ import annotations

import json
from pathlib import Path

from cloudeyes_agent.profiles.general import GeneralProfileConfig, run_general_profile
from cloudeyes_core.serialization import to_primitive
from jsonschema import Draft202012Validator, FormatChecker

from tests.unit.agent.test_discovery_models import make_result

ROOT = Path(__file__).resolve().parents[3]


def test_general_profile_sample_matches_core_schema(tmp_path) -> None:
    sample = run_general_profile(
        config=GeneralProfileConfig.quick(),
        discovery=make_result(),
        sample_id="general-schema-test",
        work_dir=tmp_path,
        country_code="VN",
    )
    schema = json.loads((ROOT / "schemas/sample/sample.schema.json").read_text(encoding="utf-8"))

    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    validator.validate(to_primitive(sample))


def test_general_profile_example_matches_core_schema() -> None:
    schema = json.loads((ROOT / "schemas/sample/sample.schema.json").read_text(encoding="utf-8"))
    example = json.loads(
        (ROOT / "examples/general-profile-sample.json").read_text(encoding="utf-8")
    )

    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    validator.validate(example)
