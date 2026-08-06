"""Schema contract tests for Networking Profile output."""

from __future__ import annotations

import json
from pathlib import Path

from cloudeyes_agent.profiles.networking import (
    NetworkingProfileConfig,
    NetworkScope,
    run_networking_profile,
)
from cloudeyes_core.serialization import to_primitive
from jsonschema import Draft202012Validator, FormatChecker

from tests.network_test_server import local_network_endpoint
from tests.unit.agent.test_discovery_models import make_result

ROOT = Path(__file__).resolve().parents[3]


def _validator() -> Draft202012Validator:
    schema = json.loads((ROOT / "schemas/sample/sample.schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=FormatChecker())


def test_networking_profile_sample_matches_core_schema(tmp_path) -> None:
    with local_network_endpoint() as (download_url, upload_url):
        sample = run_networking_profile(
            config=NetworkingProfileConfig.quick(
                target_url=download_url,
                upload_url=upload_url,
                scope=NetworkScope.PRIVATE,
            ),
            discovery=make_result(),
            sample_id="networking-schema-test",
            raw_output_dir=tmp_path / "raw",
            country_code="VN",
        )

    _validator().validate(to_primitive(sample))


def test_networking_profile_example_matches_core_schema() -> None:
    example = json.loads(
        (ROOT / "examples/networking-profile-sample.json").read_text(encoding="utf-8")
    )

    _validator().validate(example)
