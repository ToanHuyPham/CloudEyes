"""Schema contract tests for Web Profile output."""

from __future__ import annotations

import json
from pathlib import Path

from cloudeyes_agent.profiles.web import (
    NetworkScope,
    WebProfileConfig,
    run_web_profile,
)
from cloudeyes_core.serialization import to_primitive
from jsonschema import Draft202012Validator, FormatChecker

from tests.unit.agent.test_discovery_models import make_result
from tests.web_test_server import local_web_endpoint

ROOT = Path(__file__).resolve().parents[3]


def _validator() -> Draft202012Validator:
    schema = json.loads((ROOT / "schemas/sample/sample.schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=FormatChecker())


def test_web_profile_sample_matches_core_schema(tmp_path) -> None:
    with local_web_endpoint() as base_url:
        sample = run_web_profile(
            config=WebProfileConfig.quick(
                target_url=f"{base_url}/ok",
                scope=NetworkScope.PRIVATE,
            ),
            discovery=make_result(),
            sample_id="web-schema-test",
            raw_output_dir=tmp_path / "raw",
            country_code="VN",
        )

    _validator().validate(to_primitive(sample))


def test_web_profile_example_matches_core_schema() -> None:
    example = json.loads((ROOT / "examples/web-profile-sample.json").read_text(encoding="utf-8"))

    _validator().validate(example)
