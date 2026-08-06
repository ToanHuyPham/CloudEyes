"""Schema contract for Backend Ingestion v1 receipts."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from cloudeyes_platform.models import IngestionReceipt
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[3]


def test_ingestion_receipt_matches_schema() -> None:
    schema = json.loads(
        (ROOT / "schemas" / "ingestion-receipt-v1.schema.json").read_text(encoding="utf-8")
    )
    receipt = IngestionReceipt(
        schema_version="1.0.0",
        submission_id="submission-0123456789abcdef01234567",
        status="accepted",
        received_at=datetime(2026, 8, 6, 12, 0, tzinfo=UTC),
        bundle_id="bundle-0123456789abcdef01234567",
        bundle_sha256="0" * 64,
        sample_count=1,
        file_count=1,
    ).to_dict()

    Draft202012Validator(schema, format_checker=FormatChecker()).validate(receipt)


def test_duplicate_ingestion_receipt_matches_schema() -> None:
    schema = json.loads(
        (ROOT / "schemas" / "ingestion-receipt-v1.schema.json").read_text(encoding="utf-8")
    )
    submission_id = "submission-0123456789abcdef01234567"
    receipt = IngestionReceipt(
        schema_version="1.0.0",
        submission_id=submission_id,
        status="duplicate",
        received_at=datetime(2026, 8, 6, 12, 0, tzinfo=UTC),
        bundle_id="bundle-0123456789abcdef01234567",
        bundle_sha256="0" * 64,
        sample_count=1,
        file_count=1,
        duplicate_of=submission_id,
    ).to_dict()

    Draft202012Validator(schema, format_checker=FormatChecker()).validate(receipt)
