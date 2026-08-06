"""Tests for fail-closed bundle ingestion."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta

import pytest
from cloudeyes_platform.config import IngestionConfig
from cloudeyes_platform.errors import IngestionError
from cloudeyes_platform.ingestion import MEDIA_TYPE, IngestionPipeline

from tests.platform_factory import build_test_bundle


def test_digest_mismatch_is_quarantined_without_authorization_header(tmp_path) -> None:
    payload = tmp_path / "invalid.zip"
    payload.write_bytes(b"not-a-zip")
    digest = "0" * 64
    pipeline = IngestionPipeline(IngestionConfig(tmp_path / "service"))
    headers = {
        "Authorization": "Bearer must-not-be-stored",
        "Content-Type": MEDIA_TYPE,
        "Idempotency-Key": digest,
        "X-CloudEyes-Bundle-Id": "bundle-test",
        "X-CloudEyes-Bundle-SHA256": digest,
    }

    with pytest.raises(IngestionError) as caught:
        pipeline.ingest(payload, headers=headers)

    assert caught.value.code == "bundle_digest_mismatch"
    assert caught.value.quarantine_id is not None
    metadata_path = pipeline.config.quarantine_dir / f"{caught.value.quarantine_id}.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert "authorization" not in metadata["headers"]
    assert "must-not-be-stored" not in metadata_path.read_text(encoding="utf-8")
    assert metadata["payload_retained"] is False


def test_invalid_zip_with_matching_digest_is_quarantined(tmp_path) -> None:
    payload = tmp_path / "invalid.zip"
    payload.write_bytes(b"not-a-zip")
    digest = hashlib.sha256(payload.read_bytes()).hexdigest()
    pipeline = IngestionPipeline(IngestionConfig(tmp_path / "service"))
    headers = {
        "Content-Type": MEDIA_TYPE,
        "Idempotency-Key": digest,
        "X-CloudEyes-Bundle-Id": "bundle-test",
        "X-CloudEyes-Bundle-SHA256": digest,
    }

    with pytest.raises(IngestionError, match="verification") as caught:
        pipeline.ingest(payload, headers=headers)

    assert caught.value.code == "invalid_bundle"
    assert caught.value.quarantine_id is not None


def test_idempotency_key_must_match_declared_digest(tmp_path) -> None:
    bundle, headers = build_test_bundle(tmp_path)
    headers["Idempotency-Key"] = "f" * 64
    pipeline = IngestionPipeline(IngestionConfig(tmp_path / "service"))

    with pytest.raises(IngestionError) as caught:
        pipeline.ingest(bundle, headers=headers)

    assert caught.value.status_code == 409
    assert caught.value.code == "idempotency_digest_conflict"


def test_same_sample_in_different_bundle_is_rejected(tmp_path) -> None:
    first, first_headers = build_test_bundle(tmp_path, name="first.zip")
    second, second_headers = build_test_bundle(
        tmp_path,
        name="second.zip",
        created_at=datetime(2026, 8, 6, 12, 1, tzinfo=UTC) + timedelta(seconds=1),
    )
    assert first.read_bytes() != second.read_bytes()
    pipeline = IngestionPipeline(IngestionConfig(tmp_path / "service"))
    pipeline.ingest(first, headers=first_headers)

    with pytest.raises(IngestionError) as caught:
        pipeline.ingest(second, headers=second_headers)

    assert caught.value.status_code == 409
    assert caught.value.code == "sample_already_ingested"
    assert pipeline.repository.counts()["submissions"] == 1


def test_request_size_limit_is_enforced_before_verification(tmp_path) -> None:
    bundle, headers = build_test_bundle(tmp_path)
    pipeline = IngestionPipeline(IngestionConfig(tmp_path / "service", max_request_bytes=1))

    with pytest.raises(IngestionError) as caught:
        pipeline.ingest(bundle, headers=headers)

    assert caught.value.status_code == 413
    assert caught.value.code == "request_too_large"
    assert not list(pipeline.config.quarantine_dir.glob("*.json"))


def test_verified_bundle_id_mismatch_is_quarantined(tmp_path) -> None:
    bundle, headers = build_test_bundle(tmp_path)
    headers["X-CloudEyes-Bundle-Id"] = "bundle-wrong"
    pipeline = IngestionPipeline(IngestionConfig(tmp_path / "service"))

    with pytest.raises(IngestionError) as caught:
        pipeline.ingest(bundle, headers=headers)

    assert caught.value.code == "invalid_bundle"
    assert caught.value.quarantine_id is not None
