"""Contract tests for Agent Discovery JSON schemas."""

from __future__ import annotations

import json
from pathlib import Path

from cloudeyes_agent.discovery import discover_all, to_primitive
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[3]
SCHEMA_DIRECTORY = ROOT / "schemas" / "discovery"


def _load(name: str) -> dict[str, object]:
    return json.loads((SCHEMA_DIRECTORY / name).read_text(encoding="utf-8"))


def _registry() -> Registry:
    resources = []
    for path in SCHEMA_DIRECTORY.glob("*.schema.json"):
        contents = json.loads(path.read_text(encoding="utf-8"))
        schema_id = contents.get("$id")
        if isinstance(schema_id, str):
            resources.append((schema_id, Resource.from_contents(contents)))
    return Registry().with_resources(resources)


def test_complete_discovery_matches_schema() -> None:
    schema = _load("result.schema.json")
    validator = Draft202012Validator(
        schema,
        registry=_registry(),
        format_checker=FormatChecker(),
    )

    validator.validate(to_primitive(discover_all(env={})))


def test_all_discovery_schemas_are_valid() -> None:
    for path in SCHEMA_DIRECTORY.glob("*.schema.json"):
        Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))
