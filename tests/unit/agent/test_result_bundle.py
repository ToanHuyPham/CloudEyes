"""Tests for Result Bundle v1 construction and integrity verification."""

from __future__ import annotations

import json
import zipfile
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
from cloudeyes_agent.bundle import (
    BundleBuildError,
    BundleVerificationError,
    build_bundle,
    verify_bundle,
)
from cloudeyes_core.serialization import dump

from tests.core_factory import make_sample


def _write_sample(path: Path, *, sample_id: str = "sample-001", raw_path: str | None = None):
    sample = make_sample(sample_id)
    if raw_path is not None:
        measurement = replace(sample.measurements[0], raw_output_path=raw_path)
        sample = replace(sample, measurements=(measurement,))
    dump(sample, path)
    return sample


def _manifest(bundle: Path) -> dict[str, object]:
    with zipfile.ZipFile(bundle) as archive:
        return json.loads(archive.read("manifest.json"))


def test_build_and_verify_bundle_with_raw_evidence(tmp_path: Path) -> None:
    sample_path = tmp_path / "data" / "sample.json"
    raw_path = tmp_path / "data" / "raw" / "evidence.json"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text(
        json.dumps(
            {
                "authorization": "Bearer secret",
                "endpoint": "https://user:pass@example.test/path?token=secret#fragment",
                "value": 42,
            }
        ),
        encoding="utf-8",
    )
    _write_sample(sample_path, raw_path="raw/evidence.json")
    bundle = tmp_path / "result.zip"

    manifest = build_bundle(
        (sample_path,),
        output=bundle,
        created_at=datetime(2026, 8, 6, tzinfo=UTC),
    )
    verification = verify_bundle(bundle)

    assert manifest["schema_version"] == "1.0.0"
    assert manifest["sample_count"] == 1
    assert verification.bundle_id == manifest["bundle_id"]
    assert verification.sample_count == 1
    assert verification.file_count == 2
    assert any(item.startswith("raw_evidence_redacted:") for item in verification.warnings)

    raw_bundle_path = manifest["samples"][0]["raw_evidence_paths"][0]
    with zipfile.ZipFile(bundle) as archive:
        bundled_raw = json.loads(archive.read(raw_bundle_path))
    assert bundled_raw["authorization"] == "[REDACTED]"
    assert bundled_raw["endpoint"] == "https://example.test/path"
    assert bundled_raw["value"] == 42


def test_missing_raw_evidence_fails_closed(tmp_path: Path) -> None:
    sample_path = tmp_path / "sample.json"
    _write_sample(sample_path, raw_path="raw/missing.json")

    with pytest.raises(BundleBuildError, match="raw evidence was not found"):
        build_bundle((sample_path,), output=tmp_path / "result.zip")


def test_missing_raw_evidence_can_be_recorded_as_warning(tmp_path: Path) -> None:
    sample_path = tmp_path / "sample.json"
    _write_sample(sample_path, raw_path="raw/missing.json")

    manifest = build_bundle(
        (sample_path,),
        output=tmp_path / "result.zip",
        allow_missing_raw=True,
    )

    assert manifest["policy"]["allow_missing_raw"] is True
    assert manifest["warnings"] == ["missing_raw_evidence:sample-001:missing.json"]
    assert verify_bundle(tmp_path / "result.zip").file_count == 1


def test_duplicate_sample_ids_are_rejected(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    _write_sample(first)
    _write_sample(second)

    with pytest.raises(BundleBuildError, match="duplicate sample ID"):
        build_bundle((first, second), output=tmp_path / "result.zip")


def test_invalid_sample_requires_explicit_policy(tmp_path: Path) -> None:
    sample_path = tmp_path / "invalid.json"
    sample = make_sample(
        quality_status="invalid",
        quality_errors=("benchmark_failed",),
    )
    dump(sample, sample_path)

    with pytest.raises(BundleBuildError, match="is invalid"):
        build_bundle((sample_path,), output=tmp_path / "rejected.zip")

    manifest = build_bundle(
        (sample_path,),
        output=tmp_path / "allowed.zip",
        allow_invalid_samples=True,
    )
    assert manifest["policy"]["allow_invalid_samples"] is True
    assert "invalid_sample_included:sample-001" in manifest["warnings"]
    assert verify_bundle(tmp_path / "allowed.zip").sample_count == 1


def test_tampered_payload_is_rejected(tmp_path: Path) -> None:
    sample_path = tmp_path / "sample.json"
    _write_sample(sample_path)
    bundle = tmp_path / "result.zip"
    build_bundle((sample_path,), output=bundle)

    replacement = tmp_path / "tampered.zip"
    with zipfile.ZipFile(bundle) as source, zipfile.ZipFile(replacement, "w") as target:
        for info in source.infolist():
            content = source.read(info)
            if info.filename.startswith("samples/"):
                content += b" "
            target.writestr(info, content)

    with pytest.raises(BundleVerificationError, match="size mismatch|checksum mismatch"):
        verify_bundle(replacement)


def test_unlisted_archive_payload_is_rejected(tmp_path: Path) -> None:
    sample_path = tmp_path / "sample.json"
    _write_sample(sample_path)
    bundle = tmp_path / "result.zip"
    build_bundle((sample_path,), output=bundle)

    with zipfile.ZipFile(bundle, "a") as archive:
        archive.writestr("extra.json", "{}")

    with pytest.raises(BundleVerificationError, match="unlisted payload"):
        verify_bundle(bundle)


def test_manifest_file_paths_are_stable_and_do_not_expose_local_paths(tmp_path: Path) -> None:
    source = tmp_path / "sensitive-user-folder" / "sample.json"
    _write_sample(source)
    bundle = tmp_path / "bundle.zip"

    build_bundle((source,), output=bundle)
    manifest_text = json.dumps(_manifest(bundle))

    assert "sensitive-user-folder" not in manifest_text
    assert "samples/0001.json" in manifest_text
