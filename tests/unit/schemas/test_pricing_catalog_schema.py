"""Schema contract for Normalized Pricing v1 input."""

from __future__ import annotations

import json
from pathlib import Path

from cloudeyes_core.serialization import load_pricing_catalog, to_primitive
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[3]


def test_example_pricing_catalog_matches_schema_and_model() -> None:
    path = ROOT / "examples" / "pricing" / "peer-comparison-v1.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads(
        (ROOT / "schemas" / "pricing" / "catalog-v1.schema.json").read_text(encoding="utf-8")
    )

    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(data),
        key=lambda error: tuple(str(item) for item in error.path),
    )
    assert not errors, "\n".join(error.message for error in errors)

    catalog = load_pricing_catalog(path)
    assert catalog.schema_version == "1.0.0"
    assert len(catalog.quotes) == 3
    assert to_primitive(catalog)["quotes"][0]["currency"] == "USD"
