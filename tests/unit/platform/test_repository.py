"""Tests for SQLite ingestion persistence."""

from __future__ import annotations

from cloudeyes_platform.config import IngestionConfig
from cloudeyes_platform.ingestion import IngestionPipeline

from tests.platform_factory import build_test_bundle


def test_repository_persists_submission_and_sample(tmp_path) -> None:
    bundle, headers = build_test_bundle(tmp_path)
    pipeline = IngestionPipeline(IngestionConfig(tmp_path / "service"))

    receipt = pipeline.ingest(bundle, headers=headers)

    assert receipt.status == "accepted"
    assert pipeline.repository.counts() == {
        "evidence": 0,
        "samples": 1,
        "submissions": 1,
    }
    stored = pipeline.bundle_store.destination(receipt.bundle_sha256)
    assert stored.is_file()
    assert stored.read_bytes() == bundle.read_bytes()


def test_duplicate_bundle_returns_existing_receipt(tmp_path) -> None:
    bundle, headers = build_test_bundle(tmp_path)
    pipeline = IngestionPipeline(IngestionConfig(tmp_path / "service"))

    accepted = pipeline.ingest(bundle, headers=headers)
    duplicate = pipeline.ingest(bundle, headers=headers)

    assert duplicate.status == "duplicate"
    assert duplicate.submission_id == accepted.submission_id
    assert duplicate.duplicate_of == accepted.submission_id
    assert pipeline.repository.counts()["submissions"] == 1


def test_repository_indexes_raw_evidence(tmp_path) -> None:
    bundle, headers = build_test_bundle(
        tmp_path,
        name="compute-bundle.zip",
        sample_name="compute-profile-sample.json",
    )
    pipeline = IngestionPipeline(IngestionConfig(tmp_path / "service"))

    receipt = pipeline.ingest(bundle, headers=headers)

    assert receipt.file_count == 2
    assert pipeline.repository.counts() == {
        "evidence": 1,
        "samples": 1,
        "submissions": 1,
    }
