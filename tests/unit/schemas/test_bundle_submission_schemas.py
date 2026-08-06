"""Schema contracts for Result Bundle and Submission v1."""

from __future__ import annotations

import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from cloudeyes_agent.bundle import build_bundle
from cloudeyes_core.serialization import dump, to_primitive
from jsonschema import Draft202012Validator, FormatChecker

from tests.core_factory import make_sample

ROOT = Path(__file__).resolve().parents[3]


def _schema(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_bundle_manifest_matches_schema(tmp_path: Path) -> None:
    sample = tmp_path / "sample.json"
    bundle = tmp_path / "bundle.zip"
    dump(make_sample(), sample)
    build_bundle(
        (sample,),
        output=bundle,
        created_at=datetime(2026, 8, 6, tzinfo=UTC),
    )
    with zipfile.ZipFile(bundle) as archive:
        manifest = json.loads(archive.read("manifest.json"))

    validator = Draft202012Validator(
        _schema("schemas/bundle/manifest-v1.schema.json"),
        format_checker=FormatChecker(),
    )
    validator.validate(manifest)


def test_submission_receipt_matches_schema() -> None:
    receipt = {
        "schema_version": "1.0.0",
        "submitted_at": "2026-08-06T12:00:00+00:00",
        "endpoint": "https://collector.example.test/v1/submissions",
        "bundle_id": "bundle-0123456789abcdef01234567",
        "bundle_sha256": "a" * 64,
        "status_code": 202,
        "accepted": True,
        "remote_submission_id": "submission-123",
        "response_sha256": "b" * 64,
    }
    validator = Draft202012Validator(
        _schema("schemas/sample/submission.schema.json"),
        format_checker=FormatChecker(),
    )
    validator.validate(to_primitive(receipt))
